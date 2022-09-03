# Epub generation Script for Manga and Comics

## Usage
```bash
Usage: Epub [options]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -d, --debug           run program in debug mode, enable Logging messages
  -l LANG, --lang=LANG  de (default) / en / sc / tc / mx / es / it / por / fr
                        / jp / kr
  -t TITLE, --title=TITLE
                        Title of Epub
  -a AUTHOR, --author=AUTHOR
                        Author of Epub
  -g GENRE, --genre=GENRE
                        Genres of Epub
  -i MARKER_INDEX, --marker-index=MARKER_INDEX
                        page for table of contents
  -m MARKER_TITLE, --marker-title=MARKER_TITLE
                        name for page in table of contents
  -p PUBLISHER, --publisher=PUBLISHER
                        Publisher of Epub
  -D DESCRIPTION, --describtion=DESCRIPTION
                        Description of Epub
  -s SERIES, --series=SERIES
                        Series of Epub
  -n NUMBER, --number=NUMBER
                        Description of Epub
  --jpg                 Image format (Default PNG)
  --jpeg                Image format (Default PNG)
```

## Structure of Folder
```
Title of Book/
  IMG Files of Series sorted of Page Number (Numbers %d(max amount of digits).format(default png| alternatives .jpg ir .jpeg with flags)) eg:
  000.png
  001.png
  002.png
  003.png
  004.png
  005.png
  006.png
  007.png
  008.png
  009.png
  010.png
  011.png
  012.png
  ...
```

Epub Suport Apple Books App with correct displaying

## Sample
Example Command:

`Epub -l en -t "Trapped in a Dating Sim The World of Otome Games is Tough for Mobs Vol. 5" -a "Yomu Mishima" -g Sci-Fi -g Isekai -g Adventure -g Comedy -g Mecha -g "School Life" -g Action -g Harem -g Romance -g Drama -p "Seven Seas Entertainment" -s "Trapped in a Dating Sim: The World of Otome Games is Tough for Mobs" -n 5 -i 004.xhtml -m "The Harbinger of a Collapse" -i 024.xhtml -m "Vanquishment of the Sky Pirates 1" -i 074.xhtml -m "Vanquishment of the Sky Pirates 2" -i 112.xhtml -m "Vanquishment of the Sky Pirates 3" -i 134.xhtml -m "The Right Path" -D "Angelica wasbeen working to patch things up with Olivia, but then she learns from the daughter of Count Ofree that Olivia has been forced to accompany Leon on his battle against the sky pirates! Can Leon prevail against his aerial enemies and save the kingdom, or is the whole campaign nothing but a plan by the aristocrats to eliminate both the heretical hero and the troublesome commoner girl?"`

Always the n-th i is assigned to the n-th m so that in the example for page:
| i | m |
|---|---|
| 000.xhtml | Cover |
| 004.xhtml | The Harbinger of a Collapse |
| 024.xhtml | Vanquishment of the Sky Pirates 1 |
| 074.xhtml | Vanquishment of the Sky Pirates 2 |
| 112.xhtml | Vanquishment of the Sky Pirates 3 |
| 134.xhtml | The Right Path |

Important is that instead of png or jpg, jpeg at the end you must specify the generated xhtml in the i but the number will remain the same as the image.
