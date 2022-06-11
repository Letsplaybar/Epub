#!/usr/bin/env python

import os
from optparse import OptionParser
import xml.etree.cElementTree as XTree
import re
import zipfile
from uuid import uuid4
from shutil import copyfile


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    return [atoi(c) for c in re.split(r'(\d+)', text)]

def generate_toc_html(title, page=[]):
    root = XTree.Element("html",
                         {"xmlns": "http://www.w3.org/1999/xhtml", "xmlns:epub": "http://www.idpf.org/2007/ops"})
    head = XTree.SubElement(root, "head")
    XTree.SubElement(head, "title").text = "TOC "+title
    XTree.SubElement(head, "meta", {"charset": "utf-8"})
    XTree.SubElement(head, "script", {"xmlns": "http://www.w3.org/1999/xhtml", "type": "text/javascript", "src":"js/kobo.js"})

    body = XTree.SubElement(root, "body")
    toc = XTree.SubElement(body, "section", {"epub:type": "toc"})
    XTree.SubElement(toc, "h1").text = title
    nav = XTree.SubElement(toc, "nav", {"id": "toc", "epub:type": "toc"})
    ol = XTree.SubElement(nav, "ol")
    for (site, titles) in page:
        li = XTree.SubElement(ol, "li")
        XTree.SubElement(li, "a", {"href": site}).text = titles
    landmark = XTree.SubElement(body, "nav", {"epub:type": "landmarks"})
    ol = XTree.SubElement(landmark, "ol")
    li = XTree.SubElement(ol, "li")
    XTree.SubElement(li, "a",{"epub:type": "bodymatter", "href": page[0][0]}).text = "Cover"
    tree = XTree.ElementTree(root)
    XTree.indent(tree, space="\t", level=0)
    tree.write("./" + title + "/toc.xhtml", encoding="utf-8", xml_declaration=True)


def generate_toc_ncx(title, page=[]):
    root = XTree.Element("ncx", {"xmlns": "http://www.daisy.org/z3986/2005/ncx/", "version": "2005-1"})
    head = XTree.SubElement(root, "head")
    XTree.SubElement(head, "meta", {"name": "dtb:uid", "content": "9781975336608"})
    docTitle = XTree.SubElement(root, "docTitle")
    XTree.SubElement(docTitle, "text").text= title
    navMap = XTree.SubElement(root, "navMap")
    for (site, titles) in page:
        navPoint = XTree.SubElement(navMap, "navPoint")
        navLabel = XTree.SubElement(navPoint, "navLabel")
        XTree.SubElement(navLabel, "text").text = titles
        XTree.SubElement(navPoint, "content", {"src": site})
    tree = XTree.ElementTree(root)
    XTree.indent(tree, space="\t", level=0)
    tree.write("./" + title + "/toc.ncx", encoding="utf-8", xml_declaration=True)

def generate_package_opf(title, genres=[], author=False, language=False, publisher=False, description=False, series=False, number=False, format="png"):
    root = XTree.Element("package", {"xmlns": "http://www.idpf.org/2007/opf", "version": "3.0", "unique-identifier": "uid", "prefix": "ibooks: http://vocabulary.itunes.apple.com/rdf/ibooks/vocabulary-extensions-1.0/"})
    metadata = XTree.SubElement(root, "metadata", {"xmlns:dc": "http://purl.org/dc/elements/1.1/", "xmlns:opf": "http://www.idpf.org/2007/opf"})
    XTree.SubElement(metadata, "dc:title", {"id": "id"}).text = title
    if author:
        XTree.SubElement(metadata, "dc:creator", {"id": "id-1"}).text = author
    if language:
        XTree.SubElement(metadata, "dc:language").text = language
    if publisher:
        XTree.SubElement(metadata, "dc:publisher").text = publisher
    for genre in genres:
        XTree.SubElement(metadata, "dc:subject").text = genre
    if description:
        XTree.SubElement(metadata, "dc:description").text = description
    XTree.SubElement(metadata, "dc:identifier").text = "uuid:"+str(uuid4())
    XTree.SubElement(metadata, "dc:identifier", {"id": "uid"}).text = "urn:uuid:"+str(uuid4())
    XTree.SubElement(metadata, "opf:meta", {"refines": "#id", "property": "title-type"}).text = "main"
    XTree.SubElement(metadata, "opf:meta", {"refines": "#id", "property": "file-as"}).text = title
    if series:
        XTree.SubElement(metadata, "meta",{"property": "schema:isPartOf"}).text = series
        XTree.SubElement(metadata, "meta",{"name": "calibre:series", "content": series})
    if number:
        XTree.SubElement(metadata, "meta", {"property": "schema:position"}).text = number
        XTree.SubElement(metadata, "meta",{"name": "calibre:series_index", "content": number})
    XTree.SubElement(metadata, "meta", {"name": "book-type", "content": "comic"})
    XTree.SubElement(metadata, "meta", {"name": "cover", "content": "cover"})
    XTree.SubElement(metadata, "meta", {"property": "dcterms:modified"}).text = "2000-03-24T00:00:00Z"
    XTree.SubElement(metadata, "meta", {"property": "rendition:layout"}).text = "pre-paginated"
    XTree.SubElement(metadata, "meta", {"name": "fixed-layout", "content": "true"})

    manifest = XTree.SubElement(root, "manifest")
    spine = XTree.SubElement(root, "spine", {"page-progression-direction": "rtl"})
    i=0
    count = 0
    for (base, dirs, files) in os.walk(title):
        sort_files = sorted(files, key=natural_keys)
        for file in sort_files:
            if file.endswith(".html") or file.endswith(".xhtml"):
                if "toc" in file:
                    XTree.SubElement(manifest, "item", {"id": "toc", "href": file, "media-type": "application/xhtml+xml", "properties": "nav"})
                    continue
                else:
                    XTree.SubElement(manifest, "item", {"id": "id" + str(i), "href": file, "media-type": "application/xhtml+xml", "properties": "scripted"})
                if count < 2:
                    XTree.SubElement(spine, "itemref", {"idref": "id" + str(i)})
                elif count % 2 == 1:
                    XTree.SubElement(spine, "itemref", {"idref": "id" + str(i), "properties": "page-spread-left"})
                else:
                    XTree.SubElement(spine, "itemref", {"idref": "id" + str(i), "properties": "page-spread-right"})
                count += 1
                i += 1
            elif file.endswith(format):
                if "jpg" is not format:
                    if "image" in base:
                        XTree.SubElement(manifest, "item", {"id": "id"+str(i), "href": "images/"+file, "media-type": "image/"+format})
                        i += 1
                    else:
                        XTree.SubElement(manifest, "item", {"id": "cover", "href": file, "media-type": "image/"+format})
                else:
                    if "image" in base:
                        XTree.SubElement(manifest, "item", {"id": "id"+str(i), "href": "images/"+file, "media-type": "image/jpeg"})
                        i += 1
                    else:
                        XTree.SubElement(manifest, "item", {"id": "cover", "href": file, "media-type": "image/jpeg"})
            elif file.endswith("ncx"):
                XTree.SubElement(manifest, "item", {"id": "toc.ncx", "href": file, "media-type": "application/x-dtbncx+xml"})
            else:
                if "css" in base:
                    XTree.SubElement(manifest, "item", {"id": "id"+str(i), "href": "css/"+file, "media-type": "text/css"})
                if "js" in base:
                    XTree.SubElement(manifest, "item",
                                     {"id": "id" + str(i), "href": "js/" + file, "media-type": "application/javascript"})
                i += 1
    tree = XTree.ElementTree(root)
    XTree.indent(tree, space="\t",level=0)
    tree.write("./"+title+"/metadata.opf", encoding="utf-8", xml_declaration=True)


def genereate_container_xml(title):
    root = XTree.Element("container", {"xmlns": "urn:oasis:names:tc:opendocument:xmlns:container", "version": "1.0"})
    files = XTree.SubElement(root, "rootfiles")
    XTree.SubElement(files, "rootfile", {"full-path": "metadata.opf", "media-type": "application/oebps-package+xml"})
    if not os.path.exists("./"+title+"/META-INF"):
        os.mkdir("./"+title+"/META-INF")
    tree = XTree.ElementTree(root)
    XTree.indent(tree,space="\t", level=0)
    tree.write("./"+title+"/META-INF/container.xml", encoding="utf-8", xml_declaration=True)


def e_pub_zip(file_name, folder):
    with zipfile.ZipFile(file_name, 'w') as myzip:
        myzip.writestr('mimetype', 'application/epub+zip')
    with zipfile.ZipFile(file_name, 'a') as myzip:
        for base, dirs, files in os.walk(folder):
            for ifile in files:
                fn = os.path.join(base, ifile)
                myzip.write(fn, fn.replace(folder+"\\", "").replace(folder+"/", ""))


def generate_structure(path, format="png"):
    for base, dirs, files in os.walk(path):
        for file in files:
            if not file.endswith("."+format) or "Cover" in file:
                continue
            name = file.replace("."+format, "")
            if "000" in file:
                copyfile(path+"/"+file, path+"/Cover."+format)
            if not os.path.exists(path+"/images"):
                os.mkdir(path+"/images")
                os.mkdir(path+"/css")
                os.mkdir(path+"/js")
                with open(path + "/css/reset.css", "w", encoding="utf-8") as f:
                    f.write(
                        "/* http://meyerweb.com/eric/tools/css/reset/\nv2.0 | 20110126\nLicense: none (public domain)\n*/\nhtml, body, div, span, applet, object, iframe,h1, h2, h3, h4, h5, h6, p, blockquote, pre, a, abbr, acronym, address, big, cite, code, del, dfn, em, img, ins, kbd, q, s, samp, small, strike, strong, sub, sup, tt, var, b, u, i, center, dl, dt, dd, ol, ul, li, fieldset, form, label, legend, table, caption, tbody, tfoot, thead, tr, th, td, article, aside, canvas, details, embed,  figure, figcaption, footer, header, hgroup,  menu, nav, output, ruby, section, summary, time, mark, audio, video {\nmargin: 0;\npadding: 0;\nborder: 0;\nfont-size: 100%;\nfont: inherit;\nvertical-align: baseline;\n}\na { color: black; text-decoration: none; }\n/* HTML5 display-role reset for older browsers */\narticle, aside, details, figcaption, figure, footer, header, hgroup, menu, nav, section {\ndisplay: block;\n}\nbody { line-height: 1; }\nol, ul { list-style: none; }\nblockquote, q { quotes: none; }\nblockquote:before, blockquote:after, q:before, q:after {\ncontent: "";\ncontent: none;\n}\ntable {\nborder-collapse: collapse;\nborder-spacing: 0;\n}")
                with open(path + "/css/styles.css", "w", encoding="utf-8") as f:
                    f.write(
                        "body { width: 100%; height: 100%; }\nimg.full { height: 100%; top: 0; left: 0; z-index: -1; }\n\n@media amzn-kf8\n{\n\tbody { width: auto; height: auto; }\n\timg.full { width: auto; height : auto; top : auto; left : auto;}\n}\n\nsvg {\n\tposition:absolute;\n\ttop:0;\n\tleft:0;\n\tmargin:0;\n\tpadding:0;\n\theight:100% !important;\n\tmax-width:100% !important;\n}")
                with open(path + "/css/stylesheet.css", "w", encoding="utf-8") as f:
                    f.write('@import url("reset.css");\n@import url("styles.css");')
                with open(path+"/js/kobo.js", "w", encoding="utf-8") as f:
                    f.write("var gPosition = 0;\nvar gProgress = 0;\nvar gCurrentPage = 0;\nvar gPageCount = 0;\nvar gClientHeight = null;\n\nconst kMaxFont = 0;\n\nfunction getPosition()\n{\n\treturn gPosition;\n}\n\nfunction getProgress()\n{\n\treturn gProgress;\n}\n\nfunction getPageCount()\n{\n\treturn gPageCount;\n}\n\nfunction getCurrentPage()\n{\n\treturn gCurrentPage;\n}\n\n/**\n * Setup the columns and calculate the total page count;\n */\n\nfunction setupBookColumns()\n{\n\tvar body = document.getElementsByTagName('body')[0].style;\n\tbody.marginLeft = 0;\n\tbody.marginRight = 0;\n\tbody.marginTop = 0;\n\tbody.marginBottom = 0;\n\t\n    var bc = document.getElementById('book-columns').style;\n    bc.width = (window.innerWidth * 2) + 'px !important';\n\tbc.height = (window.innerHeight-kMaxFont) + 'px !important';\n    bc.marginTop = '0px !important';\n    bc.webkitColumnWidth = window.innerWidth + 'px !important';\n    bc.webkitColumnGap = '0px';\n\tbc.overflow = 'visible';\n\n\tgCurrentPage = 1;\n\tgProgress = gPosition = 0;\n\t\n\tvar bi = document.getElementById('book-inner').style;\n\tbi.marginLeft = '0px';\n\tbi.marginRight = '0px';\n\tbi.padding = '0';\n\n\tgPageCount = document.body.scrollWidth / window.innerWidth;\n\n\t// Adjust the page count to 1 in case the initial bool-columns.clientHeight is less than the height of the screen. We only do this once.2\n\n\tif (gClientHeight < (window.innerHeight-kMaxFont)) {\n\t\tgPageCount = 1;\n\t}\n}\n\n/**\n * Columnize the document and move to the first page. The position and progress are reset/initialized\n * to 0. This should be the initial pagination request when the document is initially shown.\n */\n\nfunction paginate()\n{\t\n\t// Get the height of the page. We do this only once. In setupBookColumns we compare this\n\t// value to the height of the window and then decide wether to force the page count to one.\n\t\n\tif (gClientHeight == undefined) {\n\t\tgClientHeight = document.getElementById('book-columns').clientHeight;\n\t}\n\t\n\tsetupBookColumns();\n}\n\n/**\n * Paginate the document again and maintain the current progress. This needs to be used when\n * the content view changes size. For example because of orientation changes. The page count\n * and current page are recalculated based on the current progress.\n */\n\nfunction paginateAndMaintainProgress()\n{\n\tvar savedProgress = gProgress;\n\tsetupBookColumns();\n\tgoProgress(savedProgress);\n}\n\n/**\n * Update the progress based on the current page and page count. The progress is calculated\n * based on the top left position of the page. So the first page is 0% and the last page is\n * always below 1.0.\n */\n\nfunction updateProgress()\n{\n\tgProgress = (gCurrentPage - 1.0) / gPageCount;\n}\n\n/**\n * Move a page back if possible. The position, progress and page count are updated accordingly.\n */\n\nfunction goBack()\n{\n\tif (gCurrentPage > 1)\n\t{\n\t\tgCurrentPage--;\n\t\tgPosition -= window.innerWidth;\n\t\twindow.scrollTo(gPosition, 0);\n\t\tupdateProgress();\n\t}\n}\n\n/**\n * Move a page forward if possible. The position, progress and page count are updated accordingly.\n */\n\nfunction goForward()\n{\n\tif (gCurrentPage < gPageCount)\n\t{\n\t\tgCurrentPage++;\n\t\tgPosition += window.innerWidth;\n\t\twindow.scrollTo(gPosition, 0);\n\t\tupdateProgress();\n\t}\n}\n\n/**\n * Move directly to a page. Remember that there are no real page numbers in a reflowed\n * EPUB document. Use this only in the context of the current document.\n */\n\nfunction goPage(pageNumber)\n{\n\tif (pageNumber > 0 && pageNumber <= gPageCount)\n\t{\n\t\tgCurrentPage = pageNumber;\n\t\tgPosition = (gCurrentPage - 1) * window.innerWidth;\n\t\twindow.scrollTo(gPosition, 0);\n\t\tupdateProgress();\n\t}\n}\n\n/**\n * Go the the page with respect to progress. Assume everything has been setup.\n */\n\nfunction goProgress(progress)\n{\n\tprogress += 0.0001;\n\t\n\tvar progressPerPage = 1.0 / gPageCount;\n\tvar newPage = 0;\n\t\n\tfor (var page = 0; page < gPageCount; page++) {\n\t\tvar low = page * progressPerPage;\n\t\tvar high = low + progressPerPage;\n\t\tif (progress >= low && progress < high) {\n\t\t\tnewPage = page;\n\t\t\tbreak;\n\t\t}\n\t}\n\t\t\n\tgCurrentPage = newPage + 1;\n\tgPosition = (gCurrentPage - 1) * window.innerWidth;\n\twindow.scrollTo(gPosition, 0);\n\tupdateProgress();\t\t\n}\n\n//Set font family\nfunction setFontFamily(newFont) {\n\tdocument.body.style.fontFamily = newFont + ' !important';\n\tpaginateAndMaintainProgress();\n}\n\n//Sets font size to a relative size\nfunction setFontSize(toSize) {\n\tdocument.getElementById('book-inner').style.fontSize = toSize + 'em !important';\n\tpaginateAndMaintainProgress();\n}\n\n//Sets line height relative to font size\nfunction setLineHeight(toHeight) {\n\tdocument.getElementById('book-inner').style.lineHeight = toHeight + 'em !important';\n\tpaginateAndMaintainProgress();\n}\n\n//Enables night reading mode\nfunction enableNightReading() {\n\tdocument.body.style.backgroundColor = '#000000';\n\tvar theDiv = document.getElementById('book-inner');\n\ttheDiv.style.color = '#ffffff';\n\t\n\tvar anchorTags;\n\tanchorTags = theDiv.getElementsByTagName('a');\n\t\n\tfor (var i = 0; i < anchorTags.length; i++) {\n\t\tanchorTags[i].style.color = '#ffffff';\n\t}\n}")
            os.rename(path+"/"+file,path+"/images/"+file)
            with open(path+"/"+name+".xhtml", "w", encoding="utf-8") as f:
                f.write(
                    '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml">\n<head>\n<meta name="viewport" content="width=984, height=1429"/>\n<title>' + path + '</title>\n<link href="css/stylesheet.css" type="text/css" rel="stylesheet"/>\n\n<!-- kobo-style -->\n<script xmlns="http://www.w3.org/1999/xhtml" type="text/javascript" src="js/kobo.js"/>\n\n</head>\n<body>\n\n<div class="even">\n<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="984" height="1429" viewBox="0 0 984 1429">\n\t<image width="984" height="1429" xlink:href="images/' + name + '.'+format+'"/>\n</svg>\n\n</div>\n</body>\n</html>')
        break
    print(path+" competed!")


if __name__ == "__main__":
    parser = OptionParser(usage="Usage: %prog [options]", version="%prog 0.1")
    parser.add_option("-d", "--debug",
                      action="store_true",
                      dest="debug",
                      default=False,
                      help="run program in debug mode, enable Logging messages")
    parser.add_option("-l", "--lang",
                      action="store",
                      dest="lang",
                      default="de",
                      help="de (default) / en / sc / tc / mx / es / it / por / fr / jp / kr")
    parser.add_option("-t", "--title",
                      action="store",
                      dest="title",
                      default=False,
                      help="Title of Epub")
    parser.add_option("-a", "--author",
                      action="store",
                      dest="author",
                      default=False,
                      help="Author of Epub")
    parser.add_option("-g", "--genre",
                      action="append",
                      dest="genre",
                      default=[],
                      help="Genres of Epub")
    parser.add_option("-i", "--marker-index",
                      action="append",
                      dest="marker_index",
                      default=[],
                      help="page for table of contents")
    parser.add_option("-m", "--marker-title",
                      action="append",
                      dest="marker_title",
                      default=[],
                      help="name for page in table of contents")
    parser.add_option("-p", "--publisher",
                      action="store",
                      dest="publisher",
                      default=False,
                      help="Publisher of Epub")
    parser.add_option("-D", "--describtion",
                      action="store",
                      dest="description",
                      default=False,
                      help="Description of Epub")
    parser.add_option("-s", "--series",
                      action="store",
                      dest="series",
                      default=False,
                      help="Series of Epub")
    parser.add_option("-n", "--number",
                      action="store",
                      dest="number",
                      default=False,
                      help="Description of Epub")
    parser.add_option("--jpg",
                      action="store_const",
                      dest="format",
                      default=None,
                      const="jpg",
                      help="Image format Default PNG)")
    parser.add_option("--jpeg",
                      action="store_const",
                      dest="format",
                      default=None,
                      const="jpeg",
                      help="Image format Default PNG)")
    (options, args) = parser.parse_args()
    if len(options.marker_index) != len(options.marker_title):
        print("same amount of marker-index and marker-title requiered!")
        exit(-1)
    pages = []
    if "000.xhtml" not in options.marker_index:
        pages.append(("000.xhtml", "Cover"))
    for i in range(len(options.marker_index)):
        pages.append((options.marker_index[i],options.marker_title[i]))
    if options.title:
        try:
            path = os.path.join("./" + options.title, "META-INF")
            for (dirpath, dirnames, filenames) in os.walk(path):
                for file in filenames:
                    os.remove(os.path.join(dirpath, file))
            os.removedirs(path)
            os.remove("./"+options.title+"/metadata.opf")
        except Exception:
            pass
        generate_structure(options.title, format=options.format)
        generate_toc_html(options.title,pages)
        generate_toc_ncx(options.title, pages)
        generate_package_opf(options.title, options.genre, options.author, options.lang, options.publisher, options.description, options.series, options.number, format=options.format)
        genereate_container_xml(options.title)
        e_pub_zip(options.title+".epub", options.title)
