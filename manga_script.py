import os
import re
import zipfile
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, letter, landscape


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
    image_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(input_folder)
        for file in files
        if file.endswith(('.jpg', '.png'))
    ]
    total_width = 0
    total_pages = 0

    for image in image_files:
        with Image.open(image) as img:
            total_width += img.width
            total_pages += 1

    return total_width / total_pages

def get_minimum_page_height(input_folder):
    image_files = [f for f in os.listdir(input_folder) if f.endswith(('.jpg', '.png'))]
    total_height = 0
    total_pages = 0

    for image in image_files:
        with Image.open(os.path.join(input_folder, image)) as img:
            total_height += img.height
            total_pages += 1

    return total_height / total_pages

def organize_image_paths(image_paths, delete_initial_pages):
    page_regex = re.compile(r"p(\d{3})")
    digits_regex = re.compile(r"(\d{3,4})")

    if delete_initial_pages:
        image_paths = [image for image in image_paths if '000' not in os.path.basename(image) and '0000' not in os.path.basename(image)] 

    all_digits = all(os.path.basename(image).isdigit() for image in image_paths)
                            
    if all_digits:
        image_paths.sort(key=lambda x: int(os.path.basename(x)))
    else:
        all_pXXX = all(page_regex.search(os.path.basename(image)) for image in image_paths)
        
        if all_pXXX:
            image_paths.sort(key=lambda x: int(page_regex.search(os.path.basename(x)).group(1)))
        else:
            print("\nWARNING: Some of the image filenames don't follow the 'pXXX' format or have non-standard digits.")
            print("The function will now search for files using a simple three-digit number (XXX),")
            print("and it assumes there is only one 3-digit or 4-digit number in each filename.\n")

            user_input = input("Do you confirm that the filenames only have ONE SINGLE 3-digit or 4-digit number in their name? (y/n): ")
            print("\n")
            if user_input.lower() != 'y':
                raise ValueError("Please ensure filenames are renamed with either a 3-digit number, 4-digit, XXX or pXXX format.")

            image_paths.sort(key=lambda x: int(digits_regex.search(os.path.basename(x)).group(1)))
            
    return image_paths

def cut_double_page(image_path, manga_width, check):
    with Image.open(image_path) as img:
        img_width, img_height = img.size
        
        if check and img_width > img_height:
            middle = img_width // 2

            left_page = img.crop((0, 0, middle, img_height))
            right_page = img.crop((middle, 0, img_width, img_height))

            return left_page, right_page
        
        if not check and img_width > manga_width * 1.2: # 20% margin of error
            middle = img_width // 2

            left_page = img.crop((0, 0, middle, img_height))
            right_page = img.crop((middle, 0, img_width, img_height))

            return left_page, right_page
        else:
            return None, None

def check_if_all_pages_are_double(image_paths):
    counter = 0
    for image_path in image_paths:
        with Image.open(image_path) as img:
            img_width, img_height = img.size
            if img_width > img_height:
                counter += 1
    
    if counter > len(image_paths) * 0.70: # 70%
        print("\nWARNING: More than 70% of the images are in landscape mode (likely double pages).")
        print("This may result in incorrect splitting if not all images are double pages.")
        print("The program will attempt to split landscape images into halves.")
        print("Please verify the final PDF to ensure all pages are correct.\n")

        answer = input("Most pages will be splitted in half. Do you want to continue with this solution? (y/n): ")
        if answer.lower() == 'y':
            return True
    return False

def resize_and_save_images(image_paths, target_width_cm, input_folder):

    check = check_if_all_pages_are_double(image_paths)

    manga_width = get_average_page_width(input_folder)

    counter = 1 # First page will be 001
    double_page_paths = []
    new_image_paths = []

    for image_path in image_paths:

        print(f"Processing image number {counter}...", end="\r")
        try:
            left_page, right_page = cut_double_page(image_path, manga_width, check) 

            if left_page and right_page:
                left_page_resized = resize_image(left_page, target_width_cm, dpi=300)
                right_page_resized = resize_image(right_page, target_width_cm, dpi=300)

                left_page_path = os.path.join(input_folder, f"{str(counter+1).zfill(3)}.png")
                right_page_path = os.path.join(input_folder, f"{str(counter).zfill(3)}.png")

                left_page_resized.save(left_page_path, dpi=(300, 300))
                right_page_resized.save(right_page_path, dpi=(300, 300))
                
                new_image_paths.append(right_page_path)
                new_image_paths.append(left_page_path)

                double_page_paths.append(right_page_path)
                counter += 2
            else:
                with Image.open(image_path) as img:
                    img_resized = resize_image(img, target_width_cm, dpi=300)

                    img_page_path = os.path.join(input_folder, f"{str(counter).zfill(3)}.png")

                    img_resized.save(img_page_path, dpi=(300, 300))

                    new_image_paths.append(img_page_path)

                counter += 1

            os.remove(image_path)

        except Exception as e:
            print(f"Error processing image {image_path}: {str(e)}")
            continue
    
    return new_image_paths, double_page_paths, check

def scan_and_sort_images(input_folder, target_width_cm, delete_initial_pages):
    cbz_files = [f for f in os.listdir(input_folder) if f.endswith('.cbz')]
    zip_files = [f for f in os.listdir(input_folder) if f.endswith('.zip')]
    
    if len(cbz_files) > 1 or len(zip_files) > 1:
        raise ValueError("Please provide only one manga/book at a time.")
    if cbz_files:
        cbz_file = os.path.join(input_folder, cbz_files[0])
        extract_file(cbz_file, input_folder)
    if zip_files:
        zip_file = os.path.join(input_folder, zip_files[0])
        extract_file(zip_file, input_folder)
    
    image_paths = [
        os.path.join(root, file)
        for root, _, files in os.walk(input_folder)
        for file in files
        if file.endswith(('.jpg', '.png'))
    ]
    
    if not image_paths:
        raise ValueError("No image files found in the input folder. Make sure the files are not inside other folders.")
    
    print(f"Found {len(image_paths)} images.")

    # Organize the paths

    image_paths = organize_image_paths(image_paths, delete_initial_pages)

    image_paths, double_page_paths, check = resize_and_save_images(image_paths, target_width_cm, input_folder)

    return image_paths, double_page_paths, check

def extract_file(file, output_folder):
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(output_folder)

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

def validate_printing_order(image_paths, double_page_paths, pages_order, check):
    # print(double_page_paths)

    if pages_order == "right" and double_page_paths:
        total_pages = len(image_paths)

        for path in double_page_paths:
            index = image_paths.index(path)

            if check == False and (index == 0 or index == total_pages - 1):
                raise ValueError("The first or last page can't be a double page. Please change the order of the pages.")

            if index % 2 == 0:
                blank_page_path = add_blank_page(image_paths, input_folder='input')
                # print("Adding blank page to the beginning...")
                image_paths.insert(0, blank_page_path)
                break
    
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
        # print("Adding blank page to the end...")

    if len(image_paths) % 4 == 0:
        return image_paths
    
    # Second attempt: Remove up to 4 pages

    pages_deleted = 0
    while len(image_paths) % 4 != 0 and pages_deleted < 4:
        image_paths.pop()
        pages_deleted += 1
        # print("Deleting last page...")       

    if len(image_paths) % 4 != 0:
        raise ValueError("""
            The program couldn't create a PDF because the number of pages must be divisible by 4. 
            Two blank pages were added, and up to four pages were removed, but it wasn't enough. 
            Please delete or add pages manually until the total is divisible by 4.
        """)

    return image_paths

def get_minimum_page_height(image_paths):
    min_height = float('inf')
    for image_path in image_paths:
        try:
            with Image.open(image_path) as img:
                if img.height < min_height:
                    min_height = img.height
        except Exception as e:
            print(f"Error getting minimum height of image {image_path}: {e}")

    return min_height
	
def trim_images(image_paths):
    height = get_minimum_page_height(image_paths)
    # print(f"height: {height}")

    for image_path in image_paths:
        try:
            with Image.open(image_path) as img:
                img_width, img_height = img.size

                if img_height > height:
                    img = img.crop((0, 0, img_width, height))
                    img.save(image_path)
                    # print(f"Image {image_path} trimmed.")

        except Exception as e:
            print(f"Error trimming image {image_path}: {e}")    

def organize_printing_paths(image_paths, pages_order):
    total_pages = len(image_paths)
    new_image_paths = []

    # order: 1, 4, 3, 2
    if pages_order == "right":
        left_index = 0
        right_index = total_pages - 1

        while left_index <= right_index:
            if left_index <= right_index:
                new_image_paths.append(image_paths[left_index])
                left_index += 1
            
            if right_index >= left_index:
                new_image_paths.append(image_paths[right_index])
                right_index -= 1
            
            if right_index >= left_index:
                new_image_paths.append(image_paths[right_index])
                right_index -= 1
            
            if left_index <= right_index:
                new_image_paths.append(image_paths[left_index])
                left_index += 1

        return new_image_paths

    # order: 4, 1, 2, 3
    if pages_order == "left":
        left_index = 0
        right_index = total_pages - 1

        while left_index <= right_index:
            if right_index >= left_index:
                new_image_paths.append(image_paths[right_index])
                right_index -= 1
            
            if left_index <= right_index:
                new_image_paths.append(image_paths[left_index])
                left_index += 1
            
            if left_index <= right_index:
                new_image_paths.append(image_paths[left_index])
                left_index += 1
            
            if right_index >= left_index:
                new_image_paths.append(image_paths[right_index])
                right_index -= 1

        return new_image_paths

def pixels_to_points(pixels, dpi=300):
    return (pixels / dpi) * 72 

def draw_pdf(image_paths, output_folder, paper_size):

    paper_size_mapping = {
    "A4": A4,
    "A5": A5,
    "LETTER": letter
    }

    selected_size = paper_size_mapping[paper_size]

    output_pdf = os.path.join(output_folder, "output.pdf")
    pdf = canvas.Canvas(output_pdf, pagesize=landscape(selected_size))

    page_width, page_height = selected_size

    for i, image_path in enumerate(image_paths):
        print(f"Drawing page {i + 1} of {len(image_paths)}", end="\r")

        with Image.open(image_path) as img:
            img_width, img_height = img.size

            img_width = pixels_to_points(img_width)
            img_height = pixels_to_points(img_height)

            center_line_x = page_height / 2

            if i % 2 == 0:
                x_pos = center_line_x - img_width
            else:
                x_pos = center_line_x
            
            y_pos = (page_width - img_height) / 2

            pdf.drawImage(image_path, x_pos, y_pos, img_width, img_height)
            
            if i % 2 == 1:
                pdf.showPage()

    pdf.save()

def create_pdf(image_paths, output_folder, paper_size, pages_order, double_page_paths, check):

    print("Validating printing order...")
    image_paths = validate_printing_order(image_paths, double_page_paths, pages_order, check)
    
    print("Validating divisibility by 4...")
    image_paths = validate_divisibility_by_4(image_paths)

    print("Triming images...")
    trim_images(image_paths)

    image_paths = organize_printing_paths(image_paths, pages_order)
    # print(f"Final order of paths: {image_paths}")

    draw_pdf(image_paths, output_folder, paper_size)

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

def goodbye_message():
    print("Your PDF should be saved in the 'output' folder. For printing remember to do the following:")
    print("1. Make sure you are using the paper size you selected.")
    print("2. Use the landscape orientation.")
    print("3. If you don't have a double-side printer, make sure to first print all the odd pages, then all the even pages.")
    print("4. When the odd pages are ready, flip it 90 degrees towards the printer (so they are vertical) and put it in again.")

def create_cover(paper_size, output_folder, images_paths):

    paper_size_mapping = {
    "A4": A4,
    "A5": A5,
    "LETTER": letter
    }
    paper_size = paper_size_mapping[paper_size]

    output_pdf = os.path.join(output_folder, "cover.pdf")
    pdf = canvas.Canvas(output_pdf, pagesize=landscape(paper_size))

    page_height, page_width = paper_size

    target_height_px = get_minimum_page_height(images_paths)

    cover_folder = 'cover'
    cover_paths = [os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f.endswith(('.jpg', '.png'))]

    if not cover_paths:
        print("No cover image found. Skipping cover creation.")
        return
    if len(cover_paths) == 2 or len(cover_paths) > 3:
        print("Invalid number of cover images. It must be 1 or 3. Skipping cover creation.")
        return
    if len(cover_paths) == 1:

        with Image.open(cover_paths[0]) as img:
            img_width, img_height = img.size
            aspect_ratio = img_height / img_width

            target_width_px = int(target_height_px / aspect_ratio)
            img = img.resize((target_width_px, target_height_px))

            temp_image_path = os.path.join(output_folder, "temp_cover.jpg")
            img.save(temp_image_path, "JPEG")

            img_width_pt = pixels_to_points(img.width)
            img_height_pt = pixels_to_points(img.height)

            x_pos = (page_width - img_width_pt) / 2
            y_pos = (page_height - img_height_pt) / 2

            pdf.drawImage(temp_image_path, x_pos, y_pos, img_width_pt, img_height_pt)
            os.remove(temp_image_path)

            pdf.save()

        return
    elif len(cover_paths) == 3:
        all_digits = all(os.path.basename(cover_path).isdigit() for cover_path in cover_paths)
        
        if not all_digits:
            print("Cover images must be numbered. Skipping cover creation.")
            return

        cover_paths.sort(key=lambda x: int(os.path.basename(x).split('.')[0]))
        
        resized_images = []
        for cover_path in cover_paths:
            with Image.open(cover_path) as img:
                img_width, img_height = img.size
                aspect_ratio = img_height / img_width

                target_width_px = int(target_height_px / aspect_ratio)
                img = img.resize((target_width_px, target_height_px))

                resized_images.append(img) 
        
        total_width = sum(img.width for img in resized_images)
        combined_image = Image.new("RGB", (total_width, target_height_px))

        x_offset = 0
        for img in resized_images:
            combined_image.paste(img, (x_offset, 0))
            x_offset += img.width
        
        combined_image_path = os.path.join(output_folder, "temp_combined_cover.jpg")
        combined_image.save(combined_image_path, "JPEG")

        combined_img_width_pt = pixels_to_points(combined_image.width)
        combined_img_height_pt = pixels_to_points(combined_image.height)

        x_pos = (page_width - combined_img_width_pt) / 2
        y_pos = (page_height - combined_img_height_pt) / 2

        pdf.drawImage(combined_image_path, x_pos, y_pos, combined_img_width_pt, combined_img_height_pt)
        os.remove(combined_image_path)

        pdf.save()

def main():
    input_folder = "input"
    output_folder = "output"

    welcome_message()
    
    while True:
        print("Choose the order of the pages that you will be reading in (left [to right], or right [to left]).")
        pages_order = input("'left' is the standard order for Western countries, and 'right' is the standard for Eastern countries. ").strip().lower()

        if pages_order in ["left", "right"]:
            break

    while True:
        paper_size = input("Please choose paper size to print (A4, Letter, or A5): ").strip().upper()
        if paper_size in ["A4", "LETTER", "A5"]:
            break    

    while True:
        manga_size = input("Please choose the width of the manga/book in centimeters (usually it's 12cm) or type 'full': ").strip()
        if manga_size.isnumeric() and int(manga_size) > 0 and int(manga_size) < 20: 
            manga_size = int(manga_size)
            break
        elif manga_size == "full":
            size = {
                "A4": 14,
                "Letter": 13,
                "A5": 9,
            }
            manga_size = size[paper_size]
            break
    
    while True:     
        delete_initial_pages = input("Delete ALL '000' pages? Usually the 000 pages are covers, artwork, fanmade, etc. (y/n): ").strip().lower()
        if delete_initial_pages == "y": 
            delete_initial_pages = True
            break
        elif delete_initial_pages == "n":
            delete_initial_pages = False
            break
    print("--------------------------------------------------------------------------------------------------------")

    try:
        images_paths, double_page_paths, check = scan_and_sort_images(input_folder, manga_size, delete_initial_pages)

        create_cover(paper_size, output_folder, images_paths)    

        create_pdf(images_paths, output_folder, paper_size, pages_order, double_page_paths, check)
        
        print(f"\nPDF saved in: {output_folder}\n")

        goodbye_message()
        input("\nPress Enter to exit...")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()