#! /usr/bin/python3
# coding=utf-8

from lxml import etree
from xml.sax.saxutils import escape as xml_escape
from pprint import pprint
from pathlib import Path
import textwrap


def extract_words_from_alto_xml(filepath):
    """
    extract words from an xml file in alto format
    return list of words, each word is accompanied with metadata
    to locate its source

    """
    with filepath.open() as f:
        tree = etree.parse(f)
    words = []
    for word in tree.xpath("//String[@CONTENT]"):
        words.append({"ID": word.get("ID"),
                      "CONTENT": word.get("CONTENT"),
                      "PARENT": word.getparent().get("ID"),
                      "GRANDPARENT": word.getparent().getparent().get("ID"),
                      "PAGE_FILE": filepath,
                      })
    return words


def lookup(candidate, entities):
    """
        return first record in entities that match candidate
    """
    for record in entities:
        if candidate == record['name']:
            return record['id']
    return None


def slice(l, size):
    for i in range(len(l) + 1 - size):
        yield l[i:i+size]


def candidate2text(candidate):
    return ", ".join([w['CONTENT'] for w in candidate])


def generate_candidate_variants(candidate):
    candidate_as_str = candidate2text(candidate)
    yield candidate_as_str
    candidate_as_str = candidate2text(candidate[::-1])
    yield candidate_as_str


def look_for_entities(words, entities):
    res = []
    for candidate in slice(words, 2):
        for candidate_as_str in generate_candidate_variants(candidate):
            t = lookup(candidate_as_str, entities)
            if t:
                res.append((t, candidate, candidate_as_str))
    return res


def gather_info_from_folder(path):
    folder = Path(path)
    res = []
    l = list(folder.glob('*.xml'))
    l = sorted(l)
    for f in l:
        words = extract_words_from_alto_xml(f)
        res += words
    return res


def reverse_results(res):
    reverse_res = {}
    for r in res:
        for word in r[1]:  # this was the candidate which is a list of words
            reverse_res[word['ID']] = r[0]  # the id in the database
    return reverse_res


def generate_tei_xml(words, res):
    str = textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>
        <?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml"
            schematypens="http://purl.oclc.org/dsdl/schematron"?>
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
            <teiHeader>
                <fileDesc>
                    <titleStmt>
                        <title>Title</title>
                    </titleStmt>
                    <publicationStmt>
                        <p>Publication Information</p>
                    </publicationStmt>
                    <sourceDesc>
                        <p>Information about the source</p>
                    </sourceDesc>
                </fileDesc>
            </teiHeader>
            <text>
                <body>
                    <p>
                        {}
                    </p>
                </body>
            </text>
        </TEI>""")
    content = ""
    prev_line = None
    while words:
        word = words.pop(0)
        if prev_line != word['PARENT']:
            content += "\n</p>\n<p>\n"
        prev_line = word['PARENT']
        if res.get(word['ID'], None):
            content += '<persName corresp="{}">'.format(res[word['ID']])  # TODO DRY access ID of res
            content += xml_escape(word['CONTENT']) + ' '
            word = words.pop(0)  # for now entities are two words exactly
            content += xml_escape(word['CONTENT']) + ' '
            content += '</persName>'
        else:
            content += xml_escape(word['CONTENT']) + ' '

    return str.format(content)


if __name__ == "__main__":
    path = "../nli_entities_sample_data/additional_books/IE26721743/REP26723234/"
    words = gather_info_from_folder(path)
    print("num of words:", len(words))
    # pprint(words)
    entities = [
        {'id': 1, 'name': 'לחוק, התורהl', },
        {'id': 2, 'name': 'חייבים, לשמוע', },
        {'id': 3, 'name': 'ישראל, בניגוד', },
        {'id': 4, 'name': 'לחוק, בניגוד', },
        ]
    # TODO probably send source (name of file which contains page?) also
    res = look_for_entities(words, entities)
    print("number of result: {}".format(len(res)))
    pprint(res)
    reverse_res = reverse_results(res)
    # pprint(reverse_res)
    tei_xml = generate_tei_xml(words, reverse_res)
    with open('IE26721743_tei.xml', 'w') as f:
        f.write(tei_xml)
