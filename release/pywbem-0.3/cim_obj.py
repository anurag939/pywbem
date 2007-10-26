#! /usr/bin/python
#
# (C) Copyright 2003, 2004 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#   
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#   
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# Author: Tim Potter <tpot@hp.com>
#         Martin Pool <mbp@hp.com>

import string, UserDict
import cim_xml, cim_types
from types import StringTypes
from cim_types import atomic_to_cim_xml
from cim_xml import *

"""Representations of CIM Objects.

In general we try to map CIM objects directly into Python primitives,
except when that is not possible or would be ambiguous.  For example,
CIM Class names are simply Python strings, but a ClassPath is
represented as a special Python object.

These objects can also be mapped back into XML, by the toxml() method
which returns a string.
"""

#
# Base objects
#

class XMLObject:
    """Base class for objects that produce cim_xml document fragments."""

    def toxml(self):
        """Return the XML string representation of ourselves."""
        return self.tocimxml().toxml()


class DictObject(UserDict.UserDict):
    """Base class for objects that have a dictionary of key/value pairs.
    """

    def __cmp__(self, other):
        # The default is to compare only the dictionaries, but that is too
        # loose for our purposes.  So instead default to a very strict
        # comparison, which can be overridden in subclasses.
        if self is other:
            return 0
        else:
            return NotImplemented


    def toxml(self):
        return self.tocimxml().toxml()


#
# Object location classes
#

#
# It turns out that most of the object location elements can be
# represented easily using one base class which roughly corresponds to
# the OBJECTPATH element.
#
# Element Name        (host,       namespace,    classname, instancename)
# ---------------------------------------------------------------------------
# CLASSNAME           (None,       None,         'CIM_Foo', None)
# LOCALNAMESPACEPATH  (None,       'root/cimv2', None,      None)
# NAMESPACEPATH       ('leonardo', 'root/cimv2', None,      None)
# LOCALCLASSPATH      (None,       'root/cimv2', 'CIM_Foo', None)
# CLASSPATH           ('leonardo', 'root/cimv2', 'CIM_Foo', None)
# LOCALINSTANCEPATH   (None,       'root/cimv2', None,      InstanceName)
# INSTANCEPATH        ('leonardo', 'root/cimv2', None,      InstanceName)
#
# These guys also have string representations similar to the output
# produced by the Pegasus::CIMObjectPath.toString() method:
#
# CLASSNAME               CIM_Foo
# LOCALNAMESPACEPATH      root/cimv2:
# NAMESPACEPATH           //leonardo/root/cimv2:
# LOCALCLASSPATH          root/cimv2:CIM_Foo
# CLASSPATH               //leonardo/root/cimv2:CIM_Foo
# INSTANCENAME            CIM_Foo.Count=42,Foo="Bar"
# LOCALINSTANCEPATH       root/cimv2:CIM_Foo.Count=42,Foo="Bar"
# INSTANCEPATH            //leonardo/root/cimv2:CIM_Foo.Count=42,Foo="Bar"
#

class CIMObjectLocation(XMLObject):
    """A base class that can name any CIM object."""

    def __init__(self, host, localnamespacepath, classname, instancename):
        self.host = host
        self.localnamespacepath = localnamespacepath
        self.classname = classname
        self.instancename = instancename

    def HOST(self):
        return cim_xml.HOST(self.host)

    def CLASSNAME(self):
        return cim_xml.CLASSNAME(self.classname)

    def LOCALNAMESPACEPATH(self):
        return cim_xml.LOCALNAMESPACEPATH(
            map(cim_xml.NAMESPACE,
                string.split(self.localnamespacepath, '/')))

    def NAMESPACEPATH(self):
        return cim_xml.NAMESPACEPATH(self.HOST(), self.LOCALNAMESPACEPATH())

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMObjectLocation):
            return 1
        
        return (cmp(self.host, other.host) or
                cmp(self.localnamespacepath, other.localnamespacepath) or
                cmp(self.classname, other.classname) or
                cmp(self.instancename, other.instancename))

class CIMClassName(CIMObjectLocation):
    def __init__(self, classname):
        assert isinstance(classname, StringTypes)
        CIMObjectLocation.__init__(self, None, None, classname, None)

    def tocimxml(self):
        return self.CLASSNAME()

    def __repr__(self):
        return '%s(classname=%s)' % (self.__class__.__name__, `self.classname`)

    def __str__(self):
        return self.classname


class CIMLocalNamespacePath(CIMObjectLocation):

    def __init__(self, localnamespacepath):
        CIMObjectLocation.__init__(self, None, localnamespacepath, None, None)

    def tocimxml(self):
        return self.LOCALNAMESPACEPATH()

    def __repr__(self):
        return '%s(localnamespacepath=%s)' % \
               (self.__class__.__name__, `self.localnamespacepath`)

    def __str__(self):
        return self.localnamespacepath


class CIMNamespacePath(CIMObjectLocation):

    def __init__(self, host, localnamespacepath):
        CIMObjectLocation.__init__(self, host, localnamespacepath, None, None)

    def tocimxml(self):
        return self.NAMESPACEPATH()

    def __repr__(self):
        return '%s(host=%s, localnamespacepath=%s)' % \
               (self.__class__.__name__, `self.host`,
                `self.localnamespacepath`)

    def __str__(self):
        return '//%s/%s' % (self.host, self.localnamespacepath)


class CIMLocalClassPath(CIMObjectLocation):

    def __init__(self, localnamespacepath, classname):
        CIMObjectLocation.__init__(self, None, localnamespacepath, classname,
                                   None)

    def tocimxml(self):
        return cim_xml.LOCALCLASSPATH(self.LOCALNAMESPACEPATH(),
                                      self.CLASSNAME())

    def __repr__(self):
        return '%s(localnamespacepath=%s, classname=%s)' % \
               (self.__class__.__name__, `self.localnamespacepath`,
                `self.classname`)

    def __str__(self):
        return '%s:%s' % (self.localnamespacepath, self.classname)


class CIMClassPath(CIMObjectLocation):

    def __init__(self, host, localnamespacepath, classname):
        CIMObjectLocation.__init__(self, host, localnamespacepath, classname,
                                   None)

    def tocimxml(self):
        return cim_xml.CLASSPATH(self.NAMESPACEPATH(), self.CLASSNAME())

    def __repr__(self):
        return '%s(host=%s, localnamespacepath=%s, classname=%s)' % \
               (self.__class__.__name__, `self.host`,
                `self.localnamespacepath`, `self.classname`)

    def __str__(self):
        return '//%s/%s:%s' % (self.host, self.localnamespacepath,
                               self.classname)


class CIMLocalInstancePath(CIMObjectLocation):

    def __init__(self, localnamespacepath, instancename):
        CIMObjectLocation.__init__(self, None, localnamespacepath, None,
                                   instancename)

    def tocimxml(self):
        return cim_xml.LOCALINSTANCEPATH(self.LOCALNAMESPACEPATH(),
                                         self.instancename.tocimxml())

    def __repr__(self):
        return '%s(localnamespacepath=%s, instancename=%s)' % \
               (self.__class__.__name__, `self.localnamespacepath`,
                `self.instancename`)

    def __str__(self):
        return '%s:%s' % (self.localnamespacepath, str(self.instancename))


class CIMInstancePath(CIMObjectLocation):

    def __init__(self, host, localnamespacepath, instancename):
        CIMObjectLocation.__init__(self, host, localnamespacepath, None,
                                   instancename)

    def tocimxml(self):
        return cim_xml.INSTANCEPATH(self.NAMESPACEPATH(),
                                    self.instancename.tocimxml())

    def __repr__(self):
        return '%s(host=%s, localnamespacepath=%s, instancename=%s)' % \
               (self.__class__.__name__, `self.host`,
                `self.localnamespacepath`, `self.instancename`)

    def __str__(self):
        return '//%s/%s:%s' % (self.host, self.localnamespacepath,
                               str(self.instancename))


class CIMProperty(XMLObject):
    """A property of a CIMInstance.

    Property objects represent both properties on particular instances,
    and the property defined in a class.  In the first case, the property
    will have a Value and in the second it will not.

    The property may hold an array value, in which case it is encoded
    in XML to PROPERTY.ARRAY containing VALUE.ARRAY.

    Properties holding references are handled specially as
    CIMPropertyReference."""
    
    def __init__(self, name, type=None,
                 class_origin=None, propagated=None, value=None,
                 is_array = False, qualifiers = {}):
        """Construct a new CIMProperty

        Either the type or the value must be given.  If the value is not
        given, it is left as None.  If the type is not given, it is implied
        from the value."""
        assert isinstance(name, StringTypes)
        assert (class_origin is None) or isinstance(class_origin, StringTypes)
        assert (propagated is None) or isinstance(propagated, bool)
        self.name = name
        self.class_origin = class_origin
        self.propagated = propagated
        self.qualifiers = qualifiers
        self.is_array = is_array

        if type is None:
            assert value is not None
            self.type = cim_types.cimtype(value)
        else:
            self.type = type

        self.value = value
        

    def __repr__(self):
        r = '%s(name=%s, type=%s' % ('CIMProperty', `self.name`, `self.type`)
        if self.class_origin:
            r += ', class_origin=%s' % `self.class_origin`
        if self.propagated:
            r += ', propagated=%s' % `self.propagated`
        if self.value:
            r += ', value=%s' % `self.value`
        if self.qualifiers:
            r += ', qualifiers=' + `self.qualifiers`
        r += ')'
        return r


    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMProperty):
            return 1

        ## TODO: Allow for the type to be null as long as the values
        ## are the same and non-null?

        return (cmp(self.name, other.name)
                or cmp(self.type, other.type)
                or cmp(self.class_origin, other.class_origin)
                or cmp(self.propagated, other.propagated)
                or cmp(self.value, other.value)
                or cmp(self.qualifiers, other.qualifiers))
    

    def tocimxml(self):
        ## TODO: Have some standard function for turning CIM primitive
        ## types into their correct string representation for XML, rather than just
        ## converting to strings.
        if isinstance(self.value, list):
            va = cim_xml.VALUE_ARRAY([cim_xml.VALUE(atomic_to_cim_xml(s)) for s in self.value])
            return PROPERTY_ARRAY(name=self.name,
                                  type=self.type,
                                  value_array=va,
                                  class_origin=self.class_origin,
                                  propagated=self.propagated,
                                  qualifiers=self.qualifiers)
        else:
            return PROPERTY(name=self.name,
                            type=self.type,
                            value=VALUE(atomic_to_cim_xml(self.value)),
                            class_origin=self.class_origin,
                            propagated=self.propagated,
                            qualifiers=self.qualifiers)


class CIMPropertyReference(XMLObject):
    """A property holding a reference.

    (Not a reference to a property.)

    The reference may be either to an instance or to a class.
    """

    ## TODO: Perhaps unify this with CIMProperty?

    ## TODO: Handle qualifiers

    def __init__(self, name, value, reference_class = None,
                 class_origin = None, propagated = None):
        assert (value is None) or \
               isinstance(value, (CIMInstanceName, CIMClassName, CIMInstancePath))
        self.name = name
        self.value = value
        self.reference_class = reference_class
        self.class_origin = class_origin
        self.propagated = propagated
        self.qualifiers = {}

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, CIMPropertyReference):
            return 1

        for attr in ['name', 'value', 'reference_class', 'class_origin',
                     'propagated']:
            
            if hasattr(self, attr) and not hasattr(other, attr):
                return 1
            if not hasattr(self, attr) and hasattr(other, attr):
                return -1
            c = cmp(getattr(self, attr), getattr(other, attr))
            if c:
                return c

        return 0

    def tocimxml(self):
        return cim_xml.PROPERTY_REFERENCE(
            self.name,
            cim_xml.VALUE_REFERENCE(self.value.tocimxml()),
            reference_class = self.reference_class,
            class_origin = self.class_origin,
            propagated = self.propagated)

    def __repr__(self):
        result = '%s(name=%s, value=%s' % \
                 (self.__class__.__name__, `self.name`, `self.value`)
        if self.reference_class != None:
            result = result + ', reference_class=%s' % `self.reference_class`
        if self.class_origin != None:
            result = result + ', class_origin=%s' % `self.class_origin`
        if self.propagated != None:
            result = result + ', propagated=%s' % `self.propagated`
        result = result + ')'
        return result

    def __str__(self):
        return str(self.value)

#
# Object definition classes
#

class CIMInstanceName(DictObject):
    """Name (keys) identifying an instance.

    This may be treated as a dictionary to retrieve the keys."""

    def __init__(self, classname, bindings = {}):
        self.classname = classname
        self.data = bindings
        self.qualifiers = {}

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMInstanceName):
            return 1

        return cmp(self.classname, other.classname) or \
               cmp(self.data, other.data) or \
               cmp(self.qualifiers, other.qualifiers)

    def __str__(self):
        s = '%s.' % self.classname

        for key, value in self.data.items():
            s = s + '%s=' % key
            if type(value) == int:
                s = s + str(value)
            else:
                s = s + '"%s",' % value
        return s[:-1]

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,
                               `self.classname`,
                               `self.data`)
        
    def tocimxml(self):

        # Class with single key string property
        
        if type(self.data) == str:
            return cim_xml.INSTANCENAME(
                self.classname,
                cim_xml.KEYVALUE(self.data, 'string'))

        # Class with single key numeric property
        
        if type(self.data) == int:
            return cim_xml.INSTANCENAME(
                self.classname,
                cim_xml.KEYVALUE(str(self.data), 'numeric'))

        # Dictionary of keybindings

        if type(self.data) == dict:

            kbs = []

            for kb in self.data.items():

                # Keybindings can be integers, booleans, strings or
                # value references.                

                if hasattr(kb[1], 'tocimxml'):
                    kbs.append(cim_xml.KEYBINDING(
                        kb[0],
                        cim_xml.VALUE_REFERENCE(kb[1].tocimxml())))
                    continue
                               
                if type(kb[1]) == int:
                    _type = 'numeric'
                    value = str(kb[1])
                elif type(kb[1]) == bool:
                    _type = 'boolean'
                    if kb[1]:
                        value = 'TRUE'
                    else:
                        value = 'FALSE'
                elif type(kb[1]) == str or type(kb[1]) == unicode:
                    _type = 'string'
                    value = kb[1]
                else:
                    raise TypeError(
                        'Invalid keybinding type for keybinding ' '%s' % kb[0])

                kbs.append(cim_xml.KEYBINDING(
                    kb[0],
                    cim_xml.KEYVALUE(value, _type)))

            return cim_xml.INSTANCENAME(self.classname, kbs)

        # Value reference

        return cim_xml.INSTANCENAME(
            self.classname, cim_xml.VALUE_REFERENCE(self.data.tocimxml()))


class CIMInstance(UserDict.DictMixin):
    """Instance of a CIM Object.

    Has a classname (string), and named arrays of properties and qualifiers.

    The properties is indexed by name and points to CIMProperty
    instances."""

    ## TODO: Distinguish array from regular properties, perhaps by an
    ## is_array member.

    def __init__(self, classname, prop_bindings = {}, qualifiers = {},
                 properties = []):
        """Create CIMInstance.

        prop_bindings is a concise way to initialize property values;
        it is a dictionary from property name to value.  This is
        merely a convenience and gets the same result as the
        properties parameter.

        properties is a list of full CIMProperty objects. """
        
        assert isinstance(classname, StringTypes)
        self.classname = classname

        self.properties = {}
        for prop in properties:
            self.properties[prop.name] = prop
        
        for n, v in prop_bindings.items():
            if isinstance(v, CIMPropertyReference):
                self.properties[n] = v
            else:
                self.properties[n] = CIMProperty(n, value=v)

        self.qualifiers = qualifiers


    def __cmp__(self, other):
        if self is other:
            return 0
        if not isinstance(other, CIMInstance):
            return 1

        return (cmp(self.classname, other.classname) or
                cmp(self.properties, other.properties) or
                cmp(self.qualifiers, other.qualifiers))

    def __repr__(self):
        # Don't show all the properties and qualifiers because they're
        # just too big
        return '%s(classname=%s, ...)' % (self.__class__.__name__,
                                          `self.classname`)

    def __getitem__(self, key):
        return self.properties[key].value

    def __delitem__(self, key):
        del self.properties[key]

    def keys(self):
        return self.properties.keys()

    def __setitem__(self, key, value):

        # Don't let anyone set integer or float values.  You must use
        # a subclass from the cim_type module.

        # TODO: Lift this into a common function that checks a CIM
        # value is acceptable.

        if type(value) == int or type(value) == float or type(value) == long:
            raise TypeError('Must use a CIM type assigning numeric values.')

        self.properties[key] = CIMProperty(key, value = value)
        
    def tocimxml(self):
        props_xml = []

        for prop in self.properties.values():
            assert isinstance(prop, (CIMProperty, CIMPropertyReference))
            props_xml.append(prop.tocimxml())
            
        return cim_xml.INSTANCE(self.classname, props_xml)


class CIMNamedInstance(XMLObject):
    # Used for e.g. modifying an instance: name identifies the
    # instance to change; instance gives the new values.
    def __init__(self, name, instance):
        self.name = name
        self.instance = instance

    def tocimxml(self):
        return cim_xml.VALUE_NAMEDINSTANCE(self.name.tocimxml(),
                                           self.instance.tocimxml())

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMNamedInstance):
            return 1

        return cmp(self.name) or cmp(self.instance)
    

class CIMClass(XMLObject):
    """Class, including a description of properties, methods and qualifiers.

    superclass may be None."""
    def __init__(self, classname, properties = {}, qualifiers = {},
                 methods = {}, superclass = None):
        assert isinstance(classname, StringTypes)
        self.classname = classname
        self.properties = properties
        self.qualifiers = qualifiers
        self.methods = methods
        self.superclass = superclass

    def __repr__(self):
        return "%s(%s, ...)" % (self.__class__.__name__, `self.classname`)

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMClass):
            return 1

        return (cmp(self.classname, other.classname)
                or cmp(self.superclass, other.superclass)
                or cmp(self.properties, other.properties)
                or cmp(self.qualifiers, other.qualifiers)
                or cmp(self.methods, other.methods))

    
    def tocimxml(self):
        ## TODO: Don't we need to pack qualfiers, methods, etc?
        return cim_xml.CLASS()


class CIMMethod(DictObject):

    def __init__(self, methodname, parameters = {}, qualifiers = {}):
        self.name = methodname
        self.data = parameters
        self.qualifiers = qualifiers

    def tocimxml(self):
        return cim_xml.METHOD()

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMMethod):
            return 1

        return (cmp(self.methodname, other.methodname) or
                cmp(self.data, other.data) or
                cmp(self.qualifiers, other.qualifiers))


class CIMQualifier:
    """Represents static annotations of a class, method, property, etc.

    Includes information such as a documentation string and whether a property
    is a key."""
    def __init__(self, name, value, overridable=None, propagated=None,
                 toinstance=None, tosubclass=None, translatable=None):
        self.name = name
        self.value = value
        
        self.overridable = overridable
        self.propagated = propagated
        self.toinstance = toinstance
        self.tosubclass = tosubclass
        self.translatable = translatable
        
    def __repr__(self):
        return "%s(%s, %s, ...)" % (self.__class__.__name__,
                                    `self.name`, `self.value`)

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMQualifier):
            return 1

        return cmp(self.__dict__, other.__dict__)
    

def tocimxml(value):
    """Convert an arbitrary object to CIM xml.  Works with cim_obj
    objects and builtin types."""

    # Python cim_obj object

    if hasattr(value, 'tocimxml'):
        return value.tocimxml()

    # CIMType or builtin type

    if isinstance(value, cim_types.CIMType) or \
           type(value) in (str, unicode, int):
        return cim_xml.VALUE(unicode(value))

    if isinstance(value, bool):
        if value:
            return cim_xml.VALUE('TRUE')
        else:
            return cim_xml.VALUE('FALSE')
        raise TypeError('Invalid boolean type: %s' % value)

    # List of values

    if type(value) == list:
        return cim_xml.VALUE_ARRAY(map(tocimxml, value))

    raise ValueError("Can't convert %s (%s) to CIM XML" %
                     (`value`, type(value)))


def tocimobj(_type, value):
    """Convert a CIM type and a string value into an appropriate
    builtin type."""

    # Lists of values

    if type(value) == list:
        return map(lambda x: tocimobj(_type, x), value)

    # Boolean type
    
    if _type == 'boolean':
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        raise ValueError('Invalid boolean value "%s"' % value)

    # String type

    if _type == 'string':
        return value

    # Integer types

    if _type == 'uint8':
        return cim_types.Uint8(value)

    if _type == 'sint8':
        return cim_types.Sint8(value)

    if _type == 'uint16':
        return cim_types.Uint16(value)

    if _type == 'sint16':
        return cim_types.Sint16(value)

    if _type == 'uint32':
        return cim_types.Uint32(value)

    if _type == 'sint32':
        return cim_types.Sint32(value)

    if _type == 'uint64':
        return cim_types.Uint64(value)

    if _type == 'sint64':
        return cim_types.Sint64(value)

    # Real types

    if _type == 'real32':
        return cim_types.Real32(value)

    if _type == 'real64':
        return cim_types.Real64(value)

    # Char16

    if _type == 'char16':
        raise ValueError('CIMType char16 not handled')

    # Datetime

    if _type == 'datetime':

        if value is None:
            return None

        # TODO: The following regex only matches absolute CIM datetime
        # values, not intervals.

        import re
        if not re.match('[0-9]{14,}\.[0-9]{6,}[+-][0-9]{3,}', value):
            raise ValueError('Invalid Datetime format "%s"' % value)

        # TODO: We can probably convert the datetime value into
        # something more Pythonic like a time-tuple from the time
        # module, or a class datetime from the datetime module
        # available in Python 2.3.

        return value

    raise ValueError('Invalid CIM type "%s"' % _type)


def byname(nlist):
    """Convert a list of named objects into a map indexed by name"""
    return dict([(x.name, x) for x in nlist])