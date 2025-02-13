#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

"""
   Test of the scripts plugin

   Copyright 2010-2013 Glencoe Software, Inc. All rights reserved.
   Use is subject to license terms supplied in LICENSE.txt

"""

from builtins import str
from past.builtins import basestring
from builtins import object
import pytest
import sys
from omero.cli import CLI, NonZeroReturnCode
from omero.config import ConfigXml
from omero.install.config_parser import PropertyParser
from omero.plugins.prefs import PrefsControl, HELP
from omero.util.temp_files import create_path


try:
    basestring
except:
    basestring = str

@pytest.fixture
def configxml(monkeypatch):
    class MockConfigXml(object):
        def __init__(self, path, **kwargs):
            pass

        def as_map(self):
            return {}

        def close(self):
            pass
    monkeypatch.setattr("omero.config.ConfigXml", MockConfigXml)


class TestPrefs(object):

    def setup_method(self, method):
        self.cli = CLI()
        self.cli.register("config", PrefsControl, HELP)
        self.p = create_path()
        self.args = ["-d1", "config", "--source", "%s" % self.p]

    def config(self):
        return ConfigXml(filename=str(self.p))

    def assertStdoutStderr(self, capsys, out='', err='', strip_warning=False):
        o, e = capsys.readouterr()
        if strip_warning:
            assert(e.startswith('WARNING: '))
            e = '\n'.join(e.split('\n')[1:])
        assert (o.strip() == out and
                e.strip() == err)

    def invoke(self, s):
        if isinstance(s, basestring):
            s = s.split()
        self.cli.invoke(self.args + s, strict=True)

    def testHelp(self):
        self.invoke("-h")
        assert 0 == self.cli.rv

    @pytest.mark.parametrize('subcommand', PrefsControl().get_subcommands())
    def testSubcommandHelp(self, subcommand):
        self.invoke("%s -h" % subcommand)
        assert 0 == self.cli.rv

    def testAll(self, capsys):
        config = self.config()
        config.default("test")
        config.close()
        self.invoke("all")
        self.assertStdoutStderr(capsys, out="test\ndefault")

    def testDefaultInitial(self, capsys):
        self.invoke("def")
        self.assertStdoutStderr(capsys, out="default")

    def testDefaultEnvironment(self, capsys, monkeypatch):
        monkeypatch.setenv("OMERO_CONFIG", "testDefaultEnvironment")
        self.invoke("def")
        self.assertStdoutStderr(capsys, out="testDefaultEnvironment")

    def testDefaultSet(self, capsys):
        self.invoke("def x")
        self.assertStdoutStderr(capsys, out="x")
        self.invoke("def")
        self.assertStdoutStderr(capsys, out="x")

    def testGetSet(self, capsys):
        self.invoke("get X")
        self.assertStdoutStderr(capsys)
        self.invoke("set A B")
        self.assertStdoutStderr(capsys)
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='B')
        self.invoke("get")
        self.assertStdoutStderr(capsys, out='A=B')
        self.invoke("set A")
        self.assertStdoutStderr(capsys)
        self.invoke("keys")
        self.assertStdoutStderr(capsys)

    def testGetHidePassword(self, capsys):
        config = {
            "omero.X.mypassword": "long_password",
            "omero.X.pass": "shortpass",
            "omero.X.password": "medium_password",
            "omero.X.regular": "value",
            "omero.Y.MyPassword": "long_password",
            "omero.Y.Pass": "shortpass",
            "omero.Y.Password": "medium_password",
            "omero.Z.mypassword": "",
            "omero.Z.pass": "",
            "omero.Z.password": ""}
        output_hidden_password = (
            'omero.X.mypassword=********\n'
            'omero.X.pass=********\n'
            'omero.X.password=********\n'
            'omero.X.regular=value\n'
            'omero.Y.MyPassword=********\n'
            'omero.Y.Pass=********\n'
            'omero.Y.Password=********\n'
            'omero.Z.mypassword=\n'
            'omero.Z.pass=\n'
            'omero.Z.password=')
        output_with_password = (
            'omero.X.mypassword=long_password\n'
            'omero.X.pass=shortpass\n'
            'omero.X.password=medium_password\n'
            'omero.X.regular=value\n'
            'omero.Y.MyPassword=long_password\n'
            'omero.Y.Pass=shortpass\n'
            'omero.Y.Password=medium_password\n'
            'omero.Z.mypassword=\n'
            'omero.Z.pass=\n'
            'omero.Z.password=')

        for k, v in config.items():
            self.cli.invoke(self.args + ["set", k, v], strict=True)
        self.invoke("get")
        self.assertStdoutStderr(capsys, out=output_hidden_password)
        self.invoke("get --show-password")
        self.assertStdoutStderr(capsys, out=output_with_password)
        self.invoke("list")
        self.assertStdoutStderr(capsys, out=output_hidden_password,
                                strip_warning=True)
        self.invoke("list --show-password")
        self.assertStdoutStderr(capsys, out=output_with_password,
                                strip_warning=True)

    @pytest.mark.parametrize('argument', ['A=B', 'A= B'])
    def testSetFails(self, capsys, argument):
        self.invoke("set %s" % argument)
        self.assertStdoutStderr(
            capsys, err="\"=\" in key name. Did you mean \"...set A B\"?")

    def testKeys(self, capsys):
        self.invoke("keys")
        self.assertStdoutStderr(capsys)
        self.invoke("set A B")
        self.assertStdoutStderr(capsys)
        self.invoke("keys")
        self.assertStdoutStderr(capsys, out="A")
        self.invoke("set C D=E")
        self.assertStdoutStderr(capsys)
        self.invoke("keys")
        self.assertStdoutStderr(capsys, out="A\nC")

    def testVersion(self, capsys):
        self.invoke("version")
        self.assertStdoutStderr(capsys, out=ConfigXml.VERSION)

    def testPath(self, capsys):
        self.invoke("path")
        self.assertStdoutStderr(capsys, out=self.p)

    def testLoad(self, capsys):
        to_load = create_path()
        to_load.write_text("A=B")
        self.invoke(["load", to_load])
        self.assertStdoutStderr(capsys)
        self.invoke("get")
        self.assertStdoutStderr(capsys, out="A=B")

        # Same property/value pairs should pass
        self.invoke(["load", to_load])

        to_load.write_text("A=C")
        with pytest.raises(NonZeroReturnCode):
            # Different property/value pair should fail
            self.invoke(["load", to_load])
        self.assertStdoutStderr(
            capsys, err="Duplicate property: A ('B' => 'C')")

        # Quiet load
        self.invoke(["load", "-q", to_load])
        self.assertStdoutStderr(capsys)
        self.invoke("get")
        self.assertStdoutStderr(capsys, out="A=C")

    def testLoadDoesNotExist(self):
        # ticket:7273
        pytest.raises(NonZeroReturnCode, self.invoke,
                      "load THIS_FILE_SHOULD_NOT_EXIST")

    def testLoadMultiLine(self, capsys):
        to_load = create_path()
        to_load.write_text("A=B\\\nC")
        self.invoke(["load", to_load])
        self.invoke("get")
        self.assertStdoutStderr(capsys, out="A=BC")

    @pytest.mark.parametrize(
        'validkeyvalue',
        [('A', 'B'), ('A', 'B=C'), ('A.B', 'C.D'), ('A.B', "'C.D'")])
    def testLoadWhitelist(self, capsys, validkeyvalue):
        valid_key, valid_value = validkeyvalue
        to_load = create_path()
        to_load.write_text("%s=%s\n" % (valid_key, valid_value))
        self.invoke(["load", to_load])
        self.invoke("get %s" % valid_key)
        self.assertStdoutStderr(capsys, out=valid_value)

    @pytest.mark.parametrize(
        ('invalidline', 'invalidkey'),
        [('E F G', 'E F G'),
         ('E!F=G', 'E!F'),
         ('E = F', 'E')])
    def testLoadInvalidKey(self, capsys, invalidline, invalidkey):
        self.invoke("set A B")
        self.assertStdoutStderr(capsys)

        to_load = create_path()
        to_load.write_text("C=D\n%s\nH=I\n" % invalidline)
        with pytest.raises(NonZeroReturnCode):
            self.invoke(["load", to_load])
        self.assertStdoutStderr(
            capsys, err="Illegal property name: %s" % invalidkey)
        self.invoke("get")
        self.assertStdoutStderr(capsys, out="A=B")

    @pytest.mark.parametrize(
        'valid_key_value',
        [('A', 'B'), ('A', 'B=C'), ('A.B', 'C.D'), ('A.B', "'C.D'")])
    def testSetWhitelist(self, capsys, valid_key_value):
        valid_key, valid_value = valid_key_value
        self.invoke(["set", valid_key, valid_value])
        self.invoke(["get", valid_key])
        self.assertStdoutStderr(capsys, out=valid_value)

    @pytest.mark.parametrize('invalid_key', ['E F', 'E!F', 'E '])
    def testSetInvalidKey(self, capsys, invalid_key):
        with pytest.raises(NonZeroReturnCode):
            self.invoke(["set", invalid_key, "test"])
        self.assertStdoutStderr(
            capsys, err="Illegal property name: %s" % invalid_key.strip())

    def testSetFromFile(self, capsys):
        to_load = create_path()
        to_load.write_text("Test")
        self.invoke(["set", "-f", to_load, "A"])
        self.invoke("get")
        self.assertStdoutStderr(capsys, out="A=Test")

    def testDrop(self, capsys):
        self.invoke("def x")
        self.assertStdoutStderr(capsys, out="x")
        self.invoke("def")
        self.assertStdoutStderr(capsys, out="x")
        self.invoke("all")
        self.assertStdoutStderr(capsys, out="x\ndefault")
        self.invoke("def y")
        self.assertStdoutStderr(capsys, out="y")
        self.invoke("all")
        self.assertStdoutStderr(capsys, out="y\nx\ndefault")
        self.invoke("drop x")
        self.assertStdoutStderr(capsys)
        self.invoke("all")
        self.assertStdoutStderr(capsys, 'y\ndefault')

    def testDropFails(self, capsys):
        self.invoke("drop x")
        self.assertStdoutStderr(capsys, err="Unknown configuration: x")

    def testEdit(self):
        """
        Testing edit is a bit more complex since it wants to
        start another process. Rather than using invoke, we
        manage things ourselves here.
        """
        def fake_edit_path(tmp_file, tmp_text):
            pass
        args = self.cli.parser.parse_args("config edit".split())
        control = self.cli.controls["config"]
        config = self.config()
        try:
            control.edit(args, config, fake_edit_path)
        finally:
            config.close()

    def testNewEnvironment(self, capsys, monkeypatch):
        config = self.config()
        config.default("default")
        config.close()
        monkeypatch.setenv("OMERO_CONFIG", "testNewEnvironment")
        self.invoke("set A B")
        self.assertStdoutStderr(capsys)
        self.invoke("get")
        self.assertStdoutStderr(capsys, out="A=B")

    @pytest.mark.parametrize(
        ('initval', 'newval'),
        [('1', '2'), ('\"1\"', '\"2\"'), ('test', 'test')])
    def testAppendFails(self, initval, newval):
        self.invoke("set A %s" % initval)
        with pytest.raises(NonZeroReturnCode):
            self.invoke("append A %s" % newval)

    def testRemoveUnsetPropertyFails(self):
        with pytest.raises(NonZeroReturnCode):
            self.invoke("remove A x")

    @pytest.mark.parametrize(
        ('initval', 'newval'),
        [('1', '1'), ('[\"1\"]', '1'), ('[1]', '\"1\"')])
    def testRemoveFails(self, initval, newval):
        self.invoke("set A %s" % initval)
        with pytest.raises(NonZeroReturnCode):
            self.invoke("remove A %s" % newval)

    @pytest.mark.parametrize('report', ['--report', ''])
    def testAppendRemove(self, report, capsys):
        self.invoke("append %s A 1" % report)
        self.assertReportStdout(report, capsys, 'Appended A:1')
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='[1]')
        self.invoke("append %s A \"y\"" % report)
        self.assertReportStdout(report, capsys, 'Appended A:"y"')
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='[1, "y"]')
        self.invoke("remove %s A \"y\"" % report)
        self.assertReportStdout(report, capsys, 'Removed A:"y"')
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='[1]')
        self.invoke("remove %s A 1" % report)
        self.assertReportStdout(report, capsys, 'Removed A:1')
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='[]')

    def assertReportStdout(self, report, capsys, out):
        if report and out:
            self.assertStdoutStderr(capsys, out='Changed: %s' % out)
        else:
            self.assertStdoutStderr(capsys, out='')

    @pytest.mark.parametrize('report', ['--report', ''])
    def testAppendSet(self, report, capsys):
        self.invoke("append %s --set A 1" % report)
        self.assertReportStdout(report, capsys, 'Appended A:1')
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='[1]')
        self.invoke("append %s --set A 2" % report)
        self.assertReportStdout(report, capsys, 'Appended A:2')
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='[1, 2]')
        self.invoke("append %s --set A 1" % report)
        self.assertReportStdout(report, capsys, '')
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='[1, 2]')
        self.invoke("append %s A 1" % report)
        self.assertReportStdout(report, capsys, 'Appended A:1')
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='[1, 2, 1]')

    def testRemoveIdenticalValues(self, capsys):
        self.invoke("set A [1,1]")
        self.invoke("remove A 1")
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='[1]')
        self.invoke("remove A 1")
        self.invoke("get A")
        self.assertStdoutStderr(capsys, out='[]')

    @pytest.mark.xfail
    @pytest.mark.broken(reason = "migrate to omero-web")
    @pytest.mark.usefixtures('configxml')
    def testAppendWithDefault(self, monkeypatch, capsys):
        import json
        monkeypatch.setattr("omeroweb.settings.CUSTOM_SETTINGS_MAPPINGS", {
            "omero.web.test": ["TEST", "[1,2,3]", json.loads],
            "omero.web.notalist": ["NOTALIST", "abc", str],
        })

        self.invoke("append omero.web.test 4")
        self.invoke("get omero.web.test")
        self.assertStdoutStderr(capsys, out='[1, 2, 3, 4]')
        self.invoke("append --set omero.web.test 2")
        self.assertStdoutStderr(capsys, out='')
        self.invoke("get omero.web.test")
        self.assertStdoutStderr(capsys, out='[1, 2, 3, 4]')

        self.invoke("append omero.web.unknown 1")
        self.invoke("get omero.web.unknown")
        self.assertStdoutStderr(capsys, out='[1]')
        with pytest.raises(NonZeroReturnCode):
            self.invoke("append omero.web.notalist 1")

    @pytest.mark.xfail
    @pytest.mark.broken(reason = "migrate to omero-web")
    @pytest.mark.usefixtures('configxml')
    def testRemoveWithDefault(self, monkeypatch, capsys):
        import json
        monkeypatch.setattr("omeroweb.settings.CUSTOM_SETTINGS_MAPPINGS", {
            "omero.web.test": ["TEST", "[1,2,3]", json.loads],
        })
        self.invoke("remove omero.web.test 2")
        self.invoke("get omero.web.test")
        self.assertStdoutStderr(capsys, out='[1, 3]')
        self.invoke("remove omero.web.test 1")
        self.invoke("remove omero.web.test 3")
        self.invoke("get omero.web.test")
        self.assertStdoutStderr(capsys, out='[]')

    @pytest.mark.parametrize("data", (
        ({}, ""),
        ({"a": "b"}, "a=b"),
        ({"a": "b", "a": "d"}, "a=d"),
        ({"a": "b", "c": "d"}, "a=b\nc=d"),
        ({"c": "d", "a": "b"}, "a=b\nc=d"),
    ))
    @pytest.mark.usefixtures('configxml')
    def testList(self, data, monkeypatch, capsys):
        for k, v in list(data[0].items()):
            self.invoke("set %s %s" % (k, v))
        self.invoke("list")
        self.assertStdoutStderr(capsys, out=data[1], strip_warning=True)

    @pytest.mark.xfail
    @pytest.mark.broken(reason = "needs whitespace fixing")
    @pytest.mark.parametrize("data", (
        ("omero.a=b\nomero.c=d\n##ignore=me\n",
         "omero.a=b\nomero.c=d",
         "a (1)\n\t\nc (1)"),
        ("omero.whitelist=\\\nome.foo,\\\nome.bar\n### END",
         "omero.whitelist=ome.foo,ome.bar",
         "whitelist (1)"),
        ("omero.whitelist=\\\nome.foo,\\\nome.bar\n",
         "omero.whitelist=ome.foo,ome.bar",
         "whitelist (1)"),
        ("omero.whitelist=\\\nome.foo,\\\nome.bar",
         "omero.whitelist=ome.foo,ome.bar",
         "whitelist (1)"),
        ("omero.user_mapping=\\\na=b,c=d",
         "omero.user_mapping=a=b,c=d",
         "user_mapping (1)"),
        ("omero.whitelist=ome.foo\nIce.c=d\n",
         "Ice.c=d\nomero.whitelist=ome.foo",
         "whitelist (1)"),
        ("omero.a=b\nomero.c=d\nomero.e=f\n##ignore=me\n",
         "omero.a=b\nomero.c=d\nomero.e=f",
         "a (1)\n\t\nc (1)\n\t\ne (1)"),
        ("omero.a=b\nomero.c=d\nomero.e=f\n##ignore=me\n",
         "omero.a=b\nomero.c=d\nomero.e=f",
         "a (1)\n\t\nc (1)\n\t\ne (1)"),
    ))
    def testFileParsing(self, tmpdir, capsys, data):
        input, defaults, keys = data
        cfg = tmpdir.join("test.cfg")
        cfg.write(input)
        self.invoke("parse --file=%s --no-web" % cfg)
        self.assertStdoutStderr(capsys, out=defaults)
        self.invoke("parse --file=%s --defaults --no-web" % cfg)
        self.assertStdoutStderr(capsys, out=defaults)
        self.invoke("parse --file=%s --keys --no-web" % cfg)
        self.assertStdoutStderr(capsys, out=keys)

    @pytest.mark.parametrize("data", (
        (u"omero.ldap.base=ou=ascii\n", "ascii2"),
        (u"omero.ldap.base=ou=ascii\n", "unicodé"),
        (u"omero.ldap.base=ou=unicodé\n", "ascii"),
        (u"omero.ldap.base=ou=unicodé\n", "unicodé2"),
    ))
    def testUnicode(self, tmpdir, capsys, data):
        input, update = data
        cfg = tmpdir.join("test.cfg")
        cfg.write(input.encode("utf-8"), "wb")
        self.invoke("load %s" % cfg)  # 3 fail here
        self.invoke("get omero.ldap.base")
        self.invoke("set omero.ldap.base %s" % update)  # 1 here
        self.invoke("get omero.ldap.base")

    @pytest.mark.xfail
    def testConfigPropertyParser(self, tmpdir):
        cfg = tmpdir.join("test.properties")
        s = "a=1\nb.c=a b <!> c\nd.e=line1\\\nline2\nf.g=\\n\n"
        cfg.write(s)
        pp = PropertyParser()
        props = pp.parse_file(str(cfg))

        # Fails, the last two properties are parsed as one:
        # 'd.e' = 'line1line2f.g=\\n'
        assert len(props) == 4
        assert props[0].key == 'a'
        assert props[0].val == '1'
        assert props[1].key == 'b.c'
        assert props[1].val == 'a b <!> c'
        assert props[2].key == 'd.e'
        assert props[2].val == 'line1line2'
        assert props[3].key == 'f.g'
        assert props[3].val == '\\n'

    def testConfigNoVersionPropertyParser(self, tmpdir):
        cfg = tmpdir.join("test-noversion.properties")
        s = "omero.version=5.6.1\na.1=a\nomero.db.version=5.4.0"
        cfg.write(s)
        pp = PropertyParser()
        props = pp.parse_file(str(cfg))

        # Fails, the last two properties are parsed as one:
        # 'd.e' = 'line1line2f.g=\\n'
        assert len(props) == 2
        assert props[0].key == 'a.1'
        assert props[0].val == 'a'
        assert props[1].key == 'omero.db.version'
        assert props[1].val == '5.4.0'
