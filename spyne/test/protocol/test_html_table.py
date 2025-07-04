#!/usr/bin/env python
#
# spyne - Copyright (C) Spyne contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from lxml import etree, html

from spyne.application import Application
from spyne.decorator import srpc
from spyne.model.primitive import Integer, Unicode
from spyne.model.primitive import String
from spyne.model.primitive import AnyUri
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.protocol.http import HttpRpc
from spyne.protocol.html.table import HtmlColumnTable, HtmlRowTable
from spyne.service import Service
from spyne.server.wsgi import WsgiApplication
from spyne.util.test import show, call_wsgi_app_kwargs, call_wsgi_app


class CM(ComplexModel):
    _type_info = [
        ('i', Integer),
        ('s', String),
    ]


class CCM(ComplexModel):
    _type_info = [
        ('c', CM),
        ('i', Integer),
        ('s', String),
    ]


class TestHtmlColumnTable(unittest.TestCase):
    def test_complex_array(self):
        class SomeService(Service):
            @srpc(CCM, _returns=Array(CCM))
            def some_call(ccm):
                return [ccm] * 5

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(),
                        out_protocol=HtmlColumnTable(field_type_name_attr=None))
        server = WsgiApplication(app)

        out_string = call_wsgi_app_kwargs(server,
                ccm_i='456',
                ccm_s='def',
                ccm_c_i='123',
                ccm_c_s='abc',
            )

        elt = etree.fromstring(out_string)
        show(elt, 'TestHtmlColumnTable.test_complex_array')

        elt = html.fromstring(out_string)

        row, = elt[0] # thead
        cell = row.findall('th[@class="i"]')
        assert len(cell) == 1
        assert cell[0].text == 'i'

        cell = row.findall('th[@class="s"]')
        assert len(cell) == 1
        assert cell[0].text == 's'

        for row in elt[1]: # tbody
            cell = row.xpath('td[@class="i"]')
            assert len(cell) == 1
            assert cell[0].text == '456'

            cell = row.xpath('td[@class="c"]//td[@class="i"]')
            assert len(cell) == 1
            assert cell[0].text == '123'

            cell = row.xpath('td[@class="c"]//td[@class="s"]')
            assert len(cell) == 1
            assert cell[0].text == 'abc'

            cell = row.xpath('td[@class="s"]')
            assert len(cell) == 1
            assert cell[0].text == 'def'

    def test_string_array(self):
        class SomeService(Service):
            @srpc(String(max_occurs='unbounded'), _returns=Array(String))
            def some_call(s):
                return s

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(),
                        out_protocol=HtmlColumnTable(
                            field_name_attr=None, field_type_name_attr=None))
        server = WsgiApplication(app)

        out_string = call_wsgi_app(server, body_pairs=(('s', '1'), ('s', '2')))
        elt = etree.fromstring(out_string)
        show(elt, "TestHtmlColumnTable.test_string_array")
        assert out_string.decode('utf8') == \
          '<table class="string">' \
            '<thead>' \
              '<tr><th>some_callResponse</th></tr>' \
            '</thead>' \
            '<tbody>' \
              '<tr><td>1</td></tr>' \
              '<tr><td>2</td></tr>' \
            '</tbody>' \
          '</table>'

    def test_anyuri_string(self):
        _link = "http://arskom.com.tr/"

        class C(ComplexModel):
            c = AnyUri

        class SomeService(Service):
            @srpc(_returns=Array(C))
            def some_call():
                return [C(c=_link)]

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(),
                        out_protocol=HtmlColumnTable(field_type_name_attr=None))
        server = WsgiApplication(app)

        out_string = call_wsgi_app_kwargs(server)

        elt = html.fromstring(out_string)
        show(elt, "TestHtmlColumnTable.test_anyuri_string")
        assert elt.xpath('//td[@class="c"]')[0][0].tag == 'a'
        assert elt.xpath('//td[@class="c"]')[0][0].attrib['href'] == _link

    def test_anyuri_uri_value(self):
        _link = "http://arskom.com.tr/"
        _text = "Arskom"

        class C(ComplexModel):
            c = AnyUri

        class SomeService(Service):
            @srpc(_returns=Array(C))
            def some_call():
                return [C(c=AnyUri.Value(_link, text=_text))]

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(),
                        out_protocol=HtmlColumnTable(field_type_name_attr=None))
        server = WsgiApplication(app)

        out_string = call_wsgi_app_kwargs(server)

        elt = html.fromstring(out_string)
        print(html.tostring(elt, pretty_print=True))
        assert elt.xpath('//td[@class="c"]')[0][0].tag == 'a'
        assert elt.xpath('//td[@class="c"]')[0][0].text == _text
        assert elt.xpath('//td[@class="c"]')[0][0].attrib['href'] == _link

    def test_row_subprot(self):
        from lxml.html.builder import E
        from spyne.protocol.html import HtmlBase
        from six.moves.urllib.parse import urlencode
        from spyne.protocol.html import HtmlMicroFormat

        class SearchProtocol(HtmlBase):
            def to_parent(self, ctx, cls, inst, parent, name, **kwargs):
                s = self.to_unicode(cls._type_info['query'], inst.query)
                q = urlencode({"q": s})

                parent.write(E.a("Search %s" % inst.query,
                                              href="{}?{}".format(inst.uri, q)))

            def column_table_gen_header(self, ctx, cls, parent, name):
                parent.write(E.thead(E.th("Search",
                                                   **{'class': 'search-link'})))

            def column_table_before_row(self, ctx, cls, inst, parent, name,**_):
                ctxstack = getattr(ctx.protocol[self],
                                                   'array_subprot_ctxstack', [])

                tr_ctx = parent.element('tr')
                tr_ctx.__enter__()
                ctxstack.append(tr_ctx)

                td_ctx = parent.element('td', **{'class': "search-link"})
                td_ctx.__enter__()
                ctxstack.append(td_ctx)

                ctx.protocol[self].array_subprot_ctxstack = ctxstack

            def column_table_after_row(self, ctx, cls, inst, parent, name,
                                                                      **kwargs):
                ctxstack = ctx.protocol[self].array_subprot_ctxstack

                for elt_ctx in reversed(ctxstack):
                    elt_ctx.__exit__(None, None, None)

                del ctxstack[:]

        class Search(ComplexModel):
            query = Unicode
            uri = Unicode

        SearchTable = Array(
            Search.customize(prot=SearchProtocol()),
            prot=HtmlColumnTable(field_type_name_attr=None),
        )

        class SomeService(Service):
            @srpc(_returns=SearchTable)
            def some_call():
                return [
                    Search(query='Arskom', uri='https://www.google.com/search'),
                    Search(query='Spyne', uri='https://www.bing.com/search'),
                ]

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(),
                        out_protocol=HtmlMicroFormat())
        server = WsgiApplication(app)

        out_string = call_wsgi_app_kwargs(server)

        elt = html.fromstring(out_string)
        print(html.tostring(elt, pretty_print=True))

        assert elt.xpath('//td[@class="search-link"]/a/text()') == \
                                               ['Search Arskom', 'Search Spyne']

        assert elt.xpath('//td[@class="search-link"]/a/@href') == [
            'https://www.google.com/search?q=Arskom',
            'https://www.bing.com/search?q=Spyne',
        ]

        assert elt.xpath('//th[@class="search-link"]/text()') == ["Search"]


class TestHtmlRowTable(unittest.TestCase):
    def test_anyuri_string(self):
        _link = "http://arskom.com.tr/"

        class C(ComplexModel):
            c = AnyUri

        class SomeService(Service):
            @srpc(_returns=C)
            def some_call():
                return C(c=_link)

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(),
                           out_protocol=HtmlRowTable(field_type_name_attr=None))
        server = WsgiApplication(app)

        out_string = call_wsgi_app_kwargs(server)

        elt = html.fromstring(out_string)
        print(html.tostring(elt, pretty_print=True))
        assert elt.xpath('//td[@class="c"]')[0][0].tag == 'a'
        assert elt.xpath('//td[@class="c"]')[0][0].attrib['href'] == _link

    def test_anyuri_uri_value(self):
        _link = "http://arskom.com.tr/"
        _text = "Arskom"

        class C(ComplexModel):
            c = AnyUri

        class SomeService(Service):
            @srpc(_returns=C)
            def some_call():
                return C(c=AnyUri.Value(_link, text=_text))

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(),
                           out_protocol=HtmlRowTable(field_type_name_attr=None))
        server = WsgiApplication(app)

        out_string = call_wsgi_app_kwargs(server)

        elt = html.fromstring(out_string)
        print(html.tostring(elt, pretty_print=True))
        assert elt.xpath('//td[@class="c"]')[0][0].tag == 'a'
        assert elt.xpath('//td[@class="c"]')[0][0].text == _text
        assert elt.xpath('//td[@class="c"]')[0][0].attrib['href'] == _link

    def test_complex(self):
        class SomeService(Service):
            @srpc(CCM, _returns=CCM)
            def some_call(ccm):
                return ccm

        app = Application([SomeService], 'tns',
                           in_protocol=HttpRpc(hier_delim="_"),
                           out_protocol=HtmlRowTable(field_type_name_attr=None))

        server = WsgiApplication(app)

        out_string = call_wsgi_app_kwargs(server, 'some_call',
                         ccm_c_s='abc', ccm_c_i='123', ccm_i='456', ccm_s='def')

        elt = html.fromstring(out_string)
        show(elt, "TestHtmlRowTable.test_complex")

        # Here's what this is supposed to return
        """
        <table class="CCM">
          <tbody>
            <tr>
              <th class="i">i</th>
              <td class="i">456</td>
            </tr>
            <tr class="c">
              <th class="c">c</th>
              <td class="c">
                <table class="c">
                  <tbody>
                    <tr>
                      <th class="i">i</th>
                      <td class="i">123</td>
                    </tr>
                    <tr>
                      <th class="s">s</th>
                      <td class="s">abc</td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
            <tr>
              <th class="s">s</th>
              <td class="s">def</td>
            </tr>
          </tbody>
        </table>
        """

        print(html.tostring(elt, pretty_print=True))
        resp = elt.find_class('CCM')
        assert len(resp) == 1

        assert elt.xpath('tbody/tr/th[@class="i"]/text()')[0] == 'i'
        assert elt.xpath('tbody/tr/td[@class="i"]/text()')[0] == '456'

        assert elt.xpath('tbody/tr/td[@class="c"]//th[@class="i"]/text()')[0] == 'i'
        assert elt.xpath('tbody/tr/td[@class="c"]//td[@class="i"]/text()')[0] == '123'

        assert elt.xpath('tbody/tr/td[@class="c"]//th[@class="s"]/text()')[0] == 's'
        assert elt.xpath('tbody/tr/td[@class="c"]//td[@class="s"]/text()')[0] == 'abc'

        assert elt.xpath('tbody/tr/th[@class="s"]/text()')[0] == 's'
        assert elt.xpath('tbody/tr/td[@class="s"]/text()')[0] == 'def'

    def test_string_array(self):
        class SomeService(Service):
            @srpc(String(max_occurs='unbounded'), _returns=Array(String))
            def some_call(s):
                return s

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(),
            out_protocol=HtmlRowTable(field_name_attr=None,
                                                     field_type_name_attr=None))
        server = WsgiApplication(app)

        out_string = call_wsgi_app(server, body_pairs=(('s', '1'), ('s', '2')) )
        show(html.fromstring(out_string), 'TestHtmlRowTable.test_string_array')
        assert out_string.decode('utf8') == \
            '<div>' \
              '<table class="some_callResponse">' \
                '<tr>' \
                  '<th>string</th>' \
                  '<td>' \
                    '<table>' \
                      '<tr>' \
                        '<td>1</td>' \
                      '</tr>' \
                      '<tr>' \
                        '<td>2</td>' \
                      '</tr>' \
                    '</table>' \
                  '</td>' \
                '</tr>' \
              '</table>' \
            '</div>'

    def test_string_array_no_header(self):
        class SomeService(Service):
            @srpc(String(max_occurs='unbounded'), _returns=Array(String))
            def some_call(s):
                return s

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(),
             out_protocol=HtmlRowTable(header=False,
                               field_name_attr=None, field_type_name_attr=None))

        server = WsgiApplication(app)

        out_string = call_wsgi_app(server, body_pairs=(('s', '1'), ('s', '2')) )
        #FIXME: Needs a proper test with xpaths and all.
        show(html.fromstring(out_string), 'TestHtmlRowTable.test_string_array_no_header')
        assert out_string.decode('utf8') == \
            '<div>' \
              '<table class="some_callResponse">' \
                '<tr>' \
                  '<td>' \
                    '<table>' \
                      '<tr>' \
                        '<td>1</td>' \
                      '</tr>' \
                      '<tr>' \
                        '<td>2</td>' \
                      '</tr>' \
                    '</table>' \
                  '</td>' \
                '</tr>' \
              '</table>' \
            '</div>'


    def test_complex_array(self):
        v = [
            CM(i=1, s='a'),
            CM(i=2, s='b'),
            CM(i=3, s='c'),
            CM(i=4, s='d'),
        ]
        class SomeService(Service):
            @srpc(_returns=Array(CM))
            def some_call():
                return v

        app = Application([SomeService], 'tns', in_protocol=HttpRpc(),
                           out_protocol=HtmlRowTable(field_type_name_attr=None))
        server = WsgiApplication(app)

        out_string = call_wsgi_app_kwargs(server)
        show(html.fromstring(out_string), 'TestHtmlRowTable.test_complex_array')
        #FIXME: Needs a proper test with xpaths and all.
        assert out_string.decode('utf8') == \
            '<div>' \
              '<table class="CM">' \
                '<tbody>' \
                  '<tr>' \
                    '<th class="i">i</th>' \
                    '<td class="i">1</td>' \
                  '</tr>' \
                  '<tr>' \
                    '<th class="s">s</th>' \
                    '<td class="s">a</td>' \
                  '</tr>' \
                '</tbody>' \
              '</table>' \
              '<table class="CM">' \
                '<tbody>' \
                  '<tr>' \
                    '<th class="i">i</th>' \
                    '<td class="i">2</td>' \
                  '</tr>' \
                  '<tr>' \
                    '<th class="s">s</th>' \
                    '<td class="s">b</td>' \
                  '</tr>' \
                '</tbody>' \
              '</table>' \
              '<table class="CM">' \
                '<tbody>' \
                  '<tr>' \
                    '<th class="i">i</th>' \
                    '<td class="i">3</td>' \
                  '</tr>' \
                  '<tr>' \
                    '<th class="s">s</th>' \
                    '<td class="s">c</td>' \
                  '</tr>' \
                '</tbody>' \
              '</table>' \
              '<table class="CM">' \
                '<tbody>' \
                  '<tr>' \
                    '<th class="i">i</th>' \
                    '<td class="i">4</td>' \
                  '</tr>' \
                  '<tr>' \
                    '<th class="s">s</th>' \
                    '<td class="s">d</td>' \
                  '</tr>' \
                '</tbody>' \
              '</table>' \
            '</div>'



if __name__ == '__main__':
    unittest.main()
