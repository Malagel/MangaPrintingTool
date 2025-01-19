# Manga Printing Tool

Create a ready-to-print manga, book, or comic automatically from images.

## What problem does it solve?

For manga or book enthusiasts, printing their favorite titles can be a hassle. This tool simplifies the process with a straightforward approach: just place your files and double-click 'script.exe'. It handles almost everything, from splitting pages and resizing them to ensuring the print format is correct, so you don’t have to worry about the details. It also includes a basic cover creation tool, allowing you to quickly generate spines and back covers for your manga or books.


## How to download?
Go to to the [releases](https://github.com/Malagel/MangaPrintingTool/releases) tab and download the latest version. Unzip it and you are good to go.

## How to use it?


## How does it work?
Without wanting to bore you too much, let's dive into a somewhat detailed explanation of the program:

### Printing Tool
 -  First it organizes the images taking into account different ways of numeration and formats.
    
-  It promts you to choose size to resize the images. So if you want a manga of 10cm wide, it will do the transformations of centimeters to pixels, then pixels to points. Taking into account DPI, so 10 cm exactly will be on the paper you print
    
-  it automatically identifies the double pages and cuts them in half (if any)
    
-  it validates the correct format for printing, in theory pages must be divisible by 4 for printing correctly, and if double pages exist, all the right ones must be in an even position. If they are not valid, it creates white pages and puts them in the correct position.
    
-  it organizes the pages again in the order you want (left to right or right to left). Now they are ready to be drawn and print on both sides.
    
-  Finally it just draws the images to a PDF of the size you want and puts them side by side in the exact middle of the page.