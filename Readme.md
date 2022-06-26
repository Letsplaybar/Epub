# Epub generation Script for Manga and Comics

Usage:
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

Structure of Folder:
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
