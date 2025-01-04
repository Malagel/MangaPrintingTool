import os
import re
import zipfile
from fpdf import FPDF
from PIL import Image
from PyPDF2 import PdfWriter


def cm_to_pixels(cm, dpi):
    return int(cm * dpi / 2.54)

def resize_image(img, target_width_cm, dpi=300):
    target_width_px = cm_to_pixels(target_width_cm, dpi)
    img_width, img_height = img.size
    aspect_ratio = img_height / img_width
    target_height_px = int(target_width_px * aspect_ratio)

    img = img.resize((target_width_px, target_height_px))

    return img

def get_average_page_width(input_folder):
    image_files = [f for f in os.listdir(input_folder) if f.endswith(('.jpg', '.png'))]
    total_width = 0
    total_pages = 0

    for image in image_files:
        with Image.open(os.path.join(input_folder, image)) as img:
            total_width += img.width
            total_pages += 1

    return total_width / total_pages

def cut_double_page(image_path, manga_width):
    with Image.open(image_path) as img:
        img_width, img_height = img.size

        if img_width > manga_width:
            middle = img_width // 2

            left_page = img.crop((0, 0, middle, img_height))
            right_page = img.crop((middle, 0, img_width, img_height))

            return left_page, right_page
        else:
            return None, None

def scan_and_sort_images(input_folder, target_width_cm, cover):
    cbz_files = [f for f in os.listdir(input_folder) if f.endswith('.cbz')]
    zip_files = [f for f in os.listdir(input_folder) if f.endswith('.zip')]
    
    if cbz_files:
        cbz_file = os.path.join(input_folder, cbz_files[0])
        extract_file(cbz_file, input_folder)
    if zip_files:
        zip_file = os.path.join(input_folder, zip_files[0])
        extract_file(zip_file, input_folder)
    
    manga_width = get_average_page_width(input_folder)

    image_paths = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.endswith(('.jpg', '.png'))]
    print(f"Found {len(image_paths)} images in {cbz_files}")

    # Organize the paths

    page_regex = re.compile(r'p(\d+)') 
    number_regex = re.compile(r'^\d+$')  

    if all(number_regex.match(os.path.splitext(os.path.basename(image))[0]) for image in image_paths):
        image_paths.sort(key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    else:
        for image in image_paths:
            image_name = os.path.basename(image)  
            if not page_regex.search(image_name):
                print(f"Error: couldn't find page number in {image_name}")
                print("Please rename the files to include the page number (e.g. p1, p2 or 1, 2 ,3, etc). All pages must be numbered the same way.") 
                raise ValueError(f"Invalid file: {image}")
        
        image_paths.sort(key=lambda x: int(page_regex.search(os.path.basename(x)).group(1)))

    print("Cutting and resizing images...")

    # Sort the images, save the cut and uncut pages in numbered order and delete the original images while also resizing them

    counter = 0
    double_page_paths = []
    for image_path in image_paths:

        print(f"Processing image number {counter}...", end="\r")
        try:
            left_page, right_page = cut_double_page(image_path, manga_width) 

            if left_page and right_page:
                left_page_resized = resize_image(left_page, target_width_cm, dpi=300)
                right_page_resized = resize_image(right_page, target_width_cm, dpi=300)

                left_page_resized.save(
                    os.path.join(input_folder, f"{str(counter+1).zfill(3)}.png"),
                    dpi=(300, 300),
                )
                right_page_resized.save(
                    os.path.join(input_folder, f"{str(counter).zfill(3)}.png"),
                    dpi=(300, 300),
                )

                double_page_paths.append(os.path.join(input_folder, f"{str(counter).zfill(3)}.png"))
                counter += 2
            else:
                with Image.open(image_path) as img:
                    img_resized = resize_image(img, target_width_cm, dpi=300)
                    img_resized.save(
                        os.path.join(input_folder, f"{str(counter).zfill(3)}.png"),
                        dpi=(300, 300),
                    )

                counter += 1

            os.remove(image_path)

        except Exception as e:
            print(f"Error processing image {image_path}: {str(e)}")
            continue

    image_paths = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.endswith('.png')]

    image_paths.sort(key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))

    if cover:
        image_paths.remove(image_paths[0])

    return image_paths, double_page_paths

def extract_file(file, output_folder):
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(output_folder)

def get_paper_dimensions(paper_size):
    paper_dimensions = {
        "A4": (210, 297),
        "Letter": (216, 279),
        "A5": (148, 210),
    }

    return paper_dimensions[paper_size]	

def add_blank_page(image_paths, input_folder):
    counter = 0
    while True:
        blank_page_path = os.path.join(input_folder, f"blank_page_{counter}.png")
        if not os.path.exists(blank_page_path):
            break
        counter += 1

    with Image.open(image_paths[1]) as img:
        img_width, img_height = img.size
        mode = img.mode

        if mode == "RGB":
            blank_page = Image.new(mode, (img_width, img_height), color=(255, 255, 255))
        else:
            blank_page = Image.new(mode, (img_width, img_height), color=255)
        
        blank_page.save(blank_page_path)
        
    return blank_page_path

def validate_printing_order(image_paths, double_page_paths, pages_order):
    print(double_page_paths)

    if pages_order == "left" and double_page_paths:
        total_pages = len(image_paths)

        for path in double_page_paths:
            index = image_paths.index(path)

            if index == 0 or index == total_pages - 1:
                raise ValueError("The first or last page can't be a double page. Please change the order of the pages.")

            if index % 2 == 0:
                blank_page_path = add_blank_page(image_paths, input_folder='input')
                image_paths.insert(0, blank_page_path)
                break
    
    print("order of double pages validated")
    return image_paths

def validate_divisibility_by_4(image_paths):
    pages_total = len(image_paths)

    if pages_total < 4:
        raise ValueError("Not enough pages to create a PDF. Please provide at least 4 pages.")
    
    if pages_total % 4 == 0:
        return image_paths
    
    # First attempt: Add 2 blank pages

    blank_pages_added = 0
    while len(image_paths) % 4 != 0 and blank_pages_added < 2:
        blank_page_path = add_blank_page(image_paths, input_folder='input')
        image_paths.append(blank_page_path)
        blank_pages_added += 1
        print("page added")

    if len(image_paths) % 4 == 0:
        return image_paths
    
    # Second attempt: Remove up to 4 pages

    pages_deleted = 0
    while len(image_paths) % 4 != 0 and pages_deleted < 4:
        image_paths.pop()
        pages_deleted += 1
        print("page deleted")

    if len(image_paths) % 4 != 0:
        raise ValueError("""
            The program couldn't create a PDF because the number of pages must be divisible by 4. 
            Two blank pages were added, and up to four pages were removed, but it wasn't enough. 
            Please delete or add pages manually until the total is divisible by 4.
        """)

    print("divisibility by 4 validated")
    return image_paths
    
def create_pdf(image_paths, output_folder, paper_size, manga_size, pages_order, double_page_paths):

    print("validating printing order...")
    image_paths = validate_printing_order(image_paths, double_page_paths, pages_order)
    
    print("validating divisibility by 4...")
    image_paths = validate_divisibility_by_4(image_paths)

    print(image_paths)

    pdf = FPDF(unit="cm", format=paper_size)

    print("Creating PDF...")

def welcome_message():
    print("--------------------------------------------------------------------------------------------------------")
    print("                                Welcome to the Manga/Book/Comic Printing Tool")
    print("--------------------------------------------------------------------------------------------------------")
    print("               This tool will help you print manga or books in the correct order and size.")
    print("          Make sure to place your pages in the 'input' folder, and just one manga/book per use.")
    print("                             They can be .zip, .cbz, .jpg, or .png files.")
    print("--------------------------------------------------------------------------------------------------------")
    print("         IMPORTANT: the files in the 'input' folder WILL be modified, so make sure to have a backup.")
    print("--------------------------------------------------------------------------------------------------------")

def main():
    input_folder = "input"
    output_folder = "output"

    welcome_message()
    
    while True:
        pages_order = input("Choose the order of the pages that you will be reading in (left, or right): ").strip().lower()
        if pages_order in ["left", "right"]:
            break

    while True:
        paper_size = input("Please choose paper size to print (A4, Letter, or A5): ").strip()
        if paper_size in ["A4", "Letter", "A5"]:
            break    

    while True:
        manga_size = input("Please choose the width of the manga/book in centimeters (usually it's 12cm) or type 'full': ").strip()
        if manga_size.isnumeric() and int(manga_size) > 0 and int(manga_size) < 30: 
            manga_size = int(manga_size)
            break
        elif manga_size == "full":
            if paper_size == "A4":
                manga_size = 14
            elif paper_size == "Letter":
                manga_size = 13
            elif paper_size == "A5":
                manga_size = 10
            break
    
    while True:
        cover = input("Do the images have a cover as FIRST page? This is because it will need to be removed (y/n): ").strip().lower()
        if cover == "y":
            cover = True
            break
        elif cover == "n":
            cover = False
            break
    print("--------------------------------------------------------------------------------------------------------")

    try:
        images_paths, double_page_paths = scan_and_sort_images(input_folder, manga_size, cover)    

        create_pdf(images_paths, output_folder, paper_size, manga_size, pages_order, double_page_paths)
        
        print()
        print(f"PDF saved in: {output_folder}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()