import os
import re
import zipfile
import random
import textwrap
from PIL import Image, ImageColor, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, letter, landscape


def cm_to_pixels(cm, dpi):
    return int(cm * dpi / 2.54)

def points_to_pixels(points, dpi=300):
    return points * (dpi / 72)

def resize_image(img, target_width_cm, dpi=300):
    target_width_px = cm_to_pixels(target_width_cm, dpi)
    img_width, img_height = img.size
    aspect_ratio = img_height / img_width
    target_height_px = int(target_width_px * aspect_ratio)

    img = img.resize((target_width_px, target_height_px), Image.Resampling.LANCZOS)

    return img

def get_average_page_width(image_files, is_path):

    # is_path must be True or False. If True, image_files is a path. If False, image_files is a list of images
    if is_path == True:
        image_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(image_files)
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

def get_average_page_height(image_files):
    total_height = 0
    total_pages = 0

    for image in image_files:
        with Image.open(image) as img:
            total_height += img.height
            total_pages += 1

    return total_height / total_pages

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
        
        if not check and img_width > manga_width * 1.3: # 30% margin of error
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

    manga_width = get_average_page_width(input_folder, True)

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
        mode = "RGB"

        blank_page = Image.new(mode, (img_width, img_height), color=(255, 255, 255))
        blank_page.save(blank_page_path)
        
    return blank_page_path

def validate_printing_order(image_paths, double_page_paths, pages_order, check):
    if pages_order == "right" and double_page_paths:
        total_pages = len(image_paths)

        for path in double_page_paths:
            index = image_paths.index(path)

            if check == False and (index == 0 or index == total_pages - 1):
                raise ValueError("The first or last page can't be a double page. Please change the order of the pages.")

            if index % 2 == 0:
                blank_page_path = add_blank_page(image_paths, input_folder='input')
                image_paths.insert(0, blank_page_path)
                break
    elif pages_order == "left" and double_page_paths:
        total_pages = len(image_paths)

        for path in double_page_paths:
            index = image_paths.index(path)

            if check == False and (index == 0 or index == total_pages - 1):
                raise ValueError("The first or last page can't be a double page. Please change the order of the pages.")

            if index % 2 == 1:
                blank_page_path = add_blank_page(image_paths, input_folder='input')
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

def hex_to_rgb(hex_color):
    return ImageColor.getrgb(hex_color)

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
    print()
    print("--------------------------------------------------------------------------------------------------------")
    print("                                Welcome to the Manga/Book/Comic Printing Tool")
    print("--------------------------------------------------------------------------------------------------------")
    print("               This tool will help you print manga or books in the correct order and size.")
    print("          Make sure to place your pages in the 'input' folder, and just one manga/book per use.")
    print("                             They can be .zip, .cbz, .jpg, or .png files.")
    print("--------------------------------------------------------------------------------------------------------")
    print("         IMPORTANT: the files in the 'input' folder WILL be modified, so make sure to have a backup.")
    print("--------------------------------------------------------------------------------------------------------")
    print()

def goodbye_message():
    print("Your PDF should be saved in the 'output' folder. For printing remember to do the following:")
    print("1. Make sure you are using the paper size you selected.")
    print("2. Use the landscape orientation.")
    print("3. If you don't have a double-side printer, make sure to first print all the odd pages, then all the even pages.")
    print("4. When the odd pages are ready, flip it 90 degrees towards the printer (so they are vertical) and put it in again.")


# Cover functions


def darken_color(color, factor):
    return tuple(max(0, int(c * factor)) for c in color)

def generate_just_cover(cover_path, target_height_px, target_width_px, spine_color, back_color, title_path, name, author, front_color, font_color):
    if not cover_path:
        font_color = hex_to_rgb(font_color)
        print("No 'cover.png' file found, creating one...")
        # Create cover image
        if not front_color:
            front_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            print("Using random color as cover color...")
        else:
            front_color = hex_to_rgb(front_color)
        cover_page = Image.new("RGBA", (target_width_px, target_height_px), color=front_color)

        # Add title
        if not title_path:
            print("No 'title.png' file found, writing the name on the cover...")

            title = name
            font_size = target_height_px // 12

            try:
                font = ImageFont.truetype("assets/custom_font.ttf", font_size)
            except IOError:
                print("'custom_font.ttf' font not found. Using default font.")
                font = ImageFont.load_default()
            
            draw = ImageDraw.Draw(cover_page)

            max_text_width = int(target_width_px * 0.85)
            lines = textwrap.wrap(title, width=max_text_width // (font_size // 2))

            line_height = font_size + 5
            y_pos = int(target_height_px * 0.05)

            for line in lines:
                text_width = draw.textlength(line, font=font)
                x_pos = (target_width_px - text_width) // 2
                draw.text((x_pos, y_pos), line, font=font, fill=font_color)
                y_pos += line_height
        else:
            with Image.open(title_path) as title_img:
                title_img = title_img.convert("RGBA")

                new_height = target_height_px // 3
                aspect_ratio = title_img.width / title_img.height
                new_width = int(new_height * aspect_ratio)
                
                title_img = title_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                x_pos = (target_width_px - new_width) // 2
                y_pos = int(target_height_px * 0.05)
                
                cover_page.paste(title_img, (x_pos, y_pos), title_img)
        
        title = author
        font_size = target_height_px // 25
        try:
            font = ImageFont.truetype("assets/custom_font.ttf", font_size)
        except IOError:
            print("'custom_font.ttf' not found. Using default font.")
            font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(cover_page)

        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x_pos = (target_width_px - text_width) // 2
        y_pos = int(target_height_px * 0.85)

        draw.text((x_pos, y_pos), title, font=font, fill=font_color)

    else:
        with Image.open(cover_path) as cover_img:
            aspect_ratio = cover_img.width / cover_img.height 
            target_width_px = int(target_height_px * aspect_ratio)

            cover_img = cover_img.resize((target_width_px, target_height_px), Image.Resampling.LANCZOS)
            cover_page = cover_img
    
    cover_page.save("cover/cover.png", dpi=(300, 300))

    if not back_color:
        back_color = cover_page.getpixel((cover_page.width // 2, cover_page.height // 2))
    else:
        back_color = hex_to_rgb(back_color)
    if not spine_color:
        spine_color = cover_page.getpixel((cover_page.width - 5, cover_page.height // 2))
    else:
        spine_color = hex_to_rgb(spine_color)
    
    return spine_color, back_color

def generate_just_spine(target_height_px, total_pages, volume_number, name, character_path, paper_thickness, spine_color, font_color, author):
    cover_folder = "cover"
    spine_path = next((os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f == "spine.png"), None)
    editorial_path = next((os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f == "editorial.png"), None)

    if not spine_path:
        font_color = hex_to_rgb(font_color)
        spacing = int(target_height_px * 0.03)
        print("No 'spine.png' file found, creating one...")

        spine_width_cm = total_pages * paper_thickness / 10 
        target_width_px = cm_to_pixels(spine_width_cm, 300)

        spine_page = Image.new("RGBA", (target_width_px, target_height_px), color=spine_color)

        # Add book/manga name

        title = str(name)
        font_size = int(target_width_px * 0.85) 

        try:
            font = ImageFont.truetype("assets/custom_font.ttf", font_size)
        except IOError:
            print("'custom_font.ttf' not found. Using default font.")
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(spine_page)

        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1] 

        text_layer = Image.new("RGBA", (text_width, text_height), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)

        adjusted_x = -bbox[0]
        adjusted_y = -bbox[1]
        text_draw.text((adjusted_x, adjusted_y), title, font=font, fill=font_color)

        rotated_text = text_layer.rotate(-90, expand=True)

        rotated_width, rotated_height = rotated_text.size
        x_pos = (target_width_px - rotated_width) // 2 
        y_pos = int(target_height_px * 0.01)  
        
        spine_page.paste(rotated_text, (x_pos, y_pos), rotated_text)

        current_height = int(text_width + y_pos) 

        # Add spine darker color, number and character image

        if volume_number != 0:            
            # Add color to spine

            darker_spine_color = darken_color(spine_color, 0.8)
            
            color_layer_height = int(target_height_px - current_height - spacing // 2)
            color_layer = Image.new("RGBA", (target_width_px, color_layer_height), color=darker_spine_color)

            spine_page.paste(color_layer, (0, target_height_px - color_layer_height), color_layer)

            # Add volume number

            volume = str(volume_number)

            font_size = int(target_width_px * 0.9) 

            try:
                font = ImageFont.truetype("assets/custom_font.ttf", font_size)
            except IOError:
                print("'custom_font.ttf' not found. Using default font.")
                font = ImageFont.load_default()
            
            draw = ImageDraw.Draw(spine_page)

            bbox = draw.textbbox((0, 0), volume, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x_pos = (target_width_px - text_width) // 2
            y_pos = int(current_height + spacing)

            current_height = y_pos + text_height + spacing

            draw.text((x_pos, y_pos), volume, font=font, fill=(255, 255, 255))

        # Add character/spine image
        if character_path:
            with Image.open(character_path) as character_image:
                character_image = character_image.convert("RGBA")

                new_width = int(target_width_px)
                aspect_ratio = character_image.height / character_image.width
                new_height = int(new_width * aspect_ratio)
                
                character_image = character_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                x_pos = (target_width_px - new_width) // 2
                y_pos = int(current_height + spacing)

                current_height = y_pos + new_height + spacing
                spine_page.paste(character_image, (x_pos, y_pos), character_image)
    
        
        # Add book/manga author

        title = str(author)
        font_size = int(target_width_px * 0.6) 
        
        try:
            font = ImageFont.truetype("assets/custom_font.ttf", font_size)
        except IOError:
            print("'custom_font.ttf' not found. Using default font.")
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(spine_page)

        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1] 

        text_layer = Image.new("RGBA", (text_width, text_height), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)

        adjusted_x = -bbox[0]
        adjusted_y = -bbox[1]
        text_draw.text((adjusted_x, adjusted_y), title, font=font, fill=font_color)

        rotated_text = text_layer.rotate(-90, expand=True)

        rotated_width, rotated_height = rotated_text.size
        x_pos = (target_width_px - rotated_width) // 2 
        y_pos = int(current_height + spacing)

        spine_page.paste(rotated_text, (x_pos, y_pos), rotated_text)

        # Add editorial PNG

        if editorial_path:
            with Image.open(editorial_path) as editorial_img:
                editorial_img = editorial_img.convert("RGBA")

                padding = 20
                new_width = int(target_width_px - padding)
                aspect_ratio = editorial_img.height / editorial_img.width
                new_height = int(new_width * aspect_ratio)
                
                editorial_img = editorial_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                x_pos = (target_width_px - new_width) // 2
                y_pos = int(target_height_px - new_height - padding // 2)

                spine_page.paste(editorial_img, (x_pos, y_pos), editorial_img)
    
    else:
        with Image.open(spine_path) as spine_img:
            aspect_ratio = spine_img.width / spine_img.height
            target_width_px = int(target_height_px * aspect_ratio)

            spine_img = spine_img.resize((target_width_px, target_height_px), Image.Resampling.LANCZOS)
            spine_page = spine_img

    spine_page.save("cover/spine.png", dpi=(300, 300))
    return

def generate_just_back_cover(cover_path, name, author, back_color, title_path, description, font_color):
    cover_folder = "cover"
    back_path = next((os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f == "back.png"), None)
    cover_path = "cover/cover.png"

    with Image.open(cover_path) as cover_img:
        target_width_px, target_height_px = cover_img.size
        
    if not back_path:
        # Create Image

        print("No 'back.png' file found, creating one...")
        back_page = Image.new("RGBA", (target_width_px, target_height_px), color=back_color)

        # Title

        title = str(name)
        font_size = target_height_px // 16

        try:
            font = ImageFont.truetype("assets/custom_font.ttf", font_size)
        except IOError:
            print("'custom_font.ttf' not found. Using default font.")
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(back_page)

        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x_pos = (target_width_px - text_width) // 2 
        y_pos = int(target_height_px * 0.05) 

        title_height_used = y_pos + text_height

        draw.text((x_pos, y_pos), title, font=font, fill=font_color)

        # Description

        if description:
            description = str(description)
            font_size = target_height_px // 42

            try:
                font = ImageFont.truetype("assets/custom_font.ttf", font_size)
            except IOError:
                print("'custom_font.ttf' not found. Using default font.")
                font = ImageFont.load_default()

            draw = ImageDraw.Draw(back_page)

            wrapped_text = textwrap.wrap(description, width=60)

            spacing = int(target_height_px * 0.08)
            y = spacing + title_height_used

            line_spacing = int(font_size * 1.2)
            for line in wrapped_text:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]

                x = (target_width_px - line_width) // 2

                draw.text((x, y), line, font=font, fill=font_color, align="center")
                y += line_spacing

        # Author

        author = str(author)
        font_size = target_height_px // 35

        try:
            font = ImageFont.truetype("assets/custom_font.ttf", font_size)
        except IOError:
            print("'custom_font.ttf' not found. Using default font.")
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(back_page)

        bbox = draw.textbbox((0, 0), author, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        author_text_width = text_width

        padding = 20
        x_pos = int(target_width_px - text_width - padding)
        y_pos = int(target_height_px * 0.95)
        draw.text((x_pos, y_pos), author, font=font, fill=font_color)

        # Title image

        if title_path:
            with Image.open(title_path) as title_image:
                title_image = title_image.convert("RGBA")

                new_width = target_width_px // 5
                aspect_ratio = title_image.height / title_image.width
                new_height = int(new_width * aspect_ratio)
                
                title_image = title_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                x_pos = int(target_width_px - new_width / 2 - author_text_width / 2 - padding)
                y_pos = int(target_height_px * 0.87)

                back_page.paste(title_image, (x_pos, y_pos), title_image)

        # Add barcode and qr code for astetiks

        try:
            # Barcode
            barcode_path = "assets/barcode.png"
            with Image.open(barcode_path) as barcode_image:
                barcode_image = barcode_image.convert("RGBA")

                new_width = target_width_px // 4
                aspect_ratio = barcode_image.height / barcode_image.width
                new_height = int(new_width * aspect_ratio)

                barcode_image = barcode_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                padding = int(target_width_px * 0.03)
                x_pos = int(padding)
                y_pos = int(target_height_px * 0.98) - new_height

                barcode_width = new_width + padding
                barcode_height = new_height

                back_page.paste(barcode_image, (x_pos, y_pos), barcode_image)
        except Exception as e:
            print(f"Error adding barcode: {e}")

        while True:
            check = input("\nDo you want to add a QR code of this tool on the back? It will look at least OK, I promise. You can also rename de qr.png with your own image... (y/n): ").strip().lower()
            if check in ["y", "n"]:
                break
        if check == "y":
            try:
                # QR code
                qr_path = "assets/qr.png"
                with Image.open(qr_path) as qr_image:
                    qr_image = qr_image.convert("RGBA")

                    new_height = barcode_height
                    new_width = new_height
                    
                    qr_image = qr_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    x_pos = int(padding + barcode_width)
                    y_pos = int(target_height_px * 0.98) - new_height

                    back_page.paste(qr_image, (x_pos, y_pos), qr_image)
            except Exception as e:
                print(f"Error adding QR code: {e}")
    else:
        with Image.open(back_path) as back_img:
            back_img = back_img.resize((target_width_px, target_height_px), Image.Resampling.LANCZOS)
            back_page = back_img
    
    back_page.save("cover/back.png", dpi=(300, 300))

def create_cover_pdf(page_height, page_width, pages_order):
    output_path = "output/cover.pdf"
    pdf = canvas.Canvas(output_path, pagesize=(page_width, page_height))

    images = ["cover/cover.png", "cover/spine.png", "cover/back.png"]
    if pages_order == "left":
        images.reverse()

    total_width_pt = 0
    image_dimensions = []
    for image in images:
        with Image.open(image) as img:
            img_width, img_height = img.size
            img_width_pt = pixels_to_points(img_width)
            img_height_pt = pixels_to_points(img_height)
            image_dimensions.append((img_width_pt, img_height_pt))
            total_width_pt += img_width_pt

    x_start = (page_width - total_width_pt) // 2
    y_start = (page_height - image_dimensions[0][1]) // 2  

    current_x = x_start
    for (image, (img_width_pt, img_height_pt)) in (zip(images, image_dimensions)):

        pdf.drawImage(image, current_x, y_start, width=img_width_pt, height=img_height_pt)

        current_x += img_width_pt

    pdf.save()
    print(f"Cover PDF created at {output_path}.")

def generate_full_cover(total_pages, volume_number, name, author, back_color, spine_color, cover_path, character_path, title_path, target_height_px, target_width_px, paper_size, front_color, pages_order, paper_thickness, font_color, description):
    page_height, page_width = paper_size

    spine_color, back_color = generate_just_cover(cover_path, 
                                                  target_height_px, 
                                                  target_width_px, 
                                                  spine_color, 
                                                  back_color,
                                                  title_path,
                                                  name,
                                                  author,
                                                  front_color,
                                                  font_color)
    
    generate_just_spine(target_height_px, 
                        total_pages, 
                        volume_number, 
                        name, 
                        character_path,
                        paper_thickness,
                        spine_color,
                        font_color,
                        author)
    
    generate_just_back_cover(cover_path,
                            name,
                            author,
                            back_color,
                            title_path,
                            description,
                            font_color)
    
    create_cover_pdf(page_height, page_width, pages_order)

def personalized_cover_creation(page_height, page_width, target_height_px, paper_size, image_paths, pages_order, target_width_px):
    if image_paths:
        while True:
            total_pages = len(image_paths)
            check = input(f"The program detected {total_pages} pages in the input folder, do you want to use them to assign the number of pages? (y/n): ").strip().lower()
            if check in ["y", "n"]:
                break
        if check != "y":
            total_pages = input("Please enter the total number of pages, or an approximate number: ").strip()
            if total_pages.isnumeric() and int(total_pages) > 0:
                total_pages = int(total_pages)
    else: 
        total_pages = input("Please enter the total number of pages, or an approximate number: ").strip()
        if total_pages.isnumeric() and int(total_pages) > 0:
            total_pages = int(total_pages)

    while True:
        paper_thickness = input("Please enter the paper thickness in mm you will be using, or enter 'default' for an average paper thickness of 0.05: ").strip()
        if paper_thickness == "default":
            paper_thickness = 0.05
            break
        if paper_thickness.isnumeric() and float(paper_thickness) > 0:
            paper_thickness = float(paper_thickness)
            break
    while True:
        volume_number = input("Please enter the volume number of the manga, if it's a book use '0': ").strip()
        if volume_number.isnumeric():
            volume_number = int(volume_number)
            break
    while True:
        name = input("Please enter the name of the manga or book for displaying (looks better with all caps for mangas and certain fonts): ")
        if name:
            break
    while True:
        author = input("Please enter the author of the manga or book for displaying: ")
        if author:
            break
    while True:
        description = input("Please enter the description of the manga or book for displaying, or enter 'skip' for no description: ")
        if description.strip() == "skip":
            description = None
            break
        else:
            break
    while True:	
        front_color = input("Please enter the hex code of the front-cover color (eg. #000000), or 'default' to let the program choose (will be omitted if you already have a cover): ").strip()
        if front_color == "default":
            front_color = None
            break
        if re.match(r'^#([A-Fa-f0-9]{6})$', front_color):
            break
    while True:	
        back_color = input("Please enter the hex code of the back-cover color (eg. #000000), or 'default' to let the program choose: ").strip()
        if back_color == "default":
            back_color = None
            break
        if re.match(r'^#([A-Fa-f0-9]{6})$', back_color):
            break
    while True:
        spine_color = input("Please enter the hex code of the spine color (eg. #000000), or 'default' to let the program choose: ").strip()
        if spine_color == "default":
            spine_color = None
            break
        if re.match(r'^#([A-Fa-f0-9]{6})$', spine_color):
            break
    while True:
        font_color = input("Please enter the hex code of the font color (eg. #000000), or 'default' to use white: ").strip()
        if font_color == "default":
            font_color = "#FFFFFF"
            break
        if re.match(r'^#([A-Fa-f0-9]{6})$', font_color):
            break
    
    cover_folder = "cover"
    cover_path = next((os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f == "cover.png"), None)
    character_path = next((os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f == "spine_image.png"), None)
    title_path = next((os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f == "title.png"), None)

    generate_full_cover(total_pages, 
                    volume_number, 
                    name, 
                    author, 
                    back_color, 
                    spine_color, 
                    cover_path, 
                    character_path, 
                    title_path, 
                    target_height_px,
                    target_width_px, 
                    paper_size,
                    front_color,
                    pages_order,
                    paper_thickness,
                    font_color,
                    description)

def welcome_message_cover():    
    print()
    print("--------------------------------------------------------------------------------------------------------")
    print("                                Welcome to the Cover Creation Tool")
    print("--------------------------------------------------------------------------------------------------------")
    print("            This tool will help you create a personalized cover for your manga or book.")
    print("    If you have a cover page, just put them inside the 'cover' folder so it can be resized correctly.")
    print("   You can put either 1 or 3 images, using 1 will resize it, if not they will be merged and resized.")
    print("                If you don't have a cover page, you will be prompted to create one.")
    print("--------------------------------------------------------------------------------------------------------")
    print()

def detect_images_in_folder(folder_path):
    image_paths = [
        os.path.join(root, file)
        for root, _, files in os.walk(folder_path)
        for file in files
        if file.endswith(('.jpg', '.png'))
    ]
    
    if not image_paths:
        return None

    return image_paths

def create_cover(paper_size, output_folder, pages_order):
    paper_size_mapping = {
    "A4": A4,
    "A5": A5,
    "LETTER": letter
    }
    paper_size = paper_size_mapping[paper_size]

    page_height, page_width = paper_size

    cover_folder = 'cover'
    cover_path = next((os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f == "cover.png"), None)
    spine_path = next((os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f == "spine.png"), None)
    back_path = next((os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f == "back.png"), None)

    image_paths = detect_images_in_folder(folder_path="input")
    if image_paths: 
        while True:
            check = input("The program detected images in the input folder, do you want to use them to assign the size (height and width) of the cover? (y/n): ")
            if check in ["y", "n"]:
                break
        if check == "y":
            target_height_px = int(get_average_page_height(image_paths))
            target_width_px = int(get_average_page_width(image_paths, False))
        else:
            while True:
                target_height_px = input("Please enter the height of the cover in pixels for resize/generate: ").strip()
                if int(target_height_px) >= points_to_pixels(page_height):
                    print("The height of the cover cannot be greater than the height of the paper.")
                elif target_height_px.isnumeric():
                    target_height_px = int(target_height_px)
                    break
            while True:
                target_width_px = input("Please enter the width of the cover in pixels for resize/generate: ").strip()
                if (target_height_px * 2.08) >= points_to_pixels(page_width):
                    print("The width of the covers and spine cannot be greater than the width of the paper.")
                elif target_width_px.isnumeric():
                    target_width_px = int(target_width_px)
                    break
    else:
        while True:
                target_height_px = input("Please enter the height of the cover in pixels for resize/generate: ").strip()
                if int(target_height_px) >= points_to_pixels(page_height):
                    print("The height of the cover cannot be greater than the height of the paper.")
                elif target_height_px.isnumeric():
                    target_height_px = int(target_height_px)
                    break
        while True:
                target_width_px = input("Please enter the width of the cover in pixels for resize/generate: ").strip()
                if (target_height_px * 2.08) >= points_to_pixels(page_width):
                    print("The width of the covers and spine cannot be greater than the width of the paper.")
                elif target_width_px.isnumeric():
                    target_width_px = int(target_width_px)
                    break
    while True:
        if not cover_path or not spine_path or not back_path:
            personalized_creation = input("You are missing images to create a full-cover. Do you want to create the missing ones? (y/n): ").strip().lower()
            if personalized_creation in ["y", "n"]:
                break
        else:
            personalized_creation = "n"
            break
    
    if personalized_creation == "y":
        print("--------------------------------------------------------------------------------------------------------")
        print("IMPORTANT: When creating a full-cover, even though it's optional, it's recommended to have:")
        print("--------------------------------------------------------------------------------------------------------")
        print("1. A single cover page (must be named 'cover.png').")
        print("2. A transparent character or image PNG to put on the spine (must be named 'spine_image.png').")
        print("3. A transparent manga or book name/title PNG (must be named 'title.png').")
        print("4. A transparent manga or book editorial PNG for the spine (must be named 'editorial.png').")
        print("4. You can have 2 of either front/back/spine covers (or none at all), it will generate the remaining one(s).")
        print("5. You have to name the parts 'back.png', 'cover.png' or 'spine.png' if you have them.")
        print("6. Everything above must be in the 'cover' folder.")
        print("7. All the assets in the 'assets' folder can be changed, you just have to rename them.")
        print("--------------------------------------------------------------------------------------------------------")

        input("\nPress Enter to continue...\n")

        personalized_cover_creation(page_height, page_width, target_height_px, paper_size, image_paths, pages_order, target_width_px)
        return

    # Create the cover from one or three images

    output_pdf = os.path.join(output_folder, "cover.pdf")
    pdf = canvas.Canvas(output_pdf, pagesize=landscape(paper_size))

    cover_folder = 'cover'
    cover_paths = [os.path.join(cover_folder, f) for f in os.listdir(cover_folder) if f.endswith(('.jpg', '.png'))]

    if not cover_paths:
        print("No cover image found. Exiting cover creation.")
        return
    if len(cover_paths) == 1:
        print("Resizing cover")
        with Image.open(cover_paths[0]) as img:
            img_width, img_height = img.size
            aspect_ratio = img_height / img_width
            if aspect_ratio > 1:
                print("The image needs to be in landscape orientation, also it needs to be all cover/spine/back pages together.")
                print("If you wish to merge the images, put the 3 images on the 'cover' folder and run again.")
                return

            target_width_px = int(target_height_px / aspect_ratio)
            img = img.resize((target_width_px, target_height_px))

            temp_image_path = os.path.join(output_folder, "temp_cover.png")
            img.save(temp_image_path, "PNG")

            img_width_pt = pixels_to_points(img.width)
            img_height_pt = pixels_to_points(img.height)

            x_pos = (page_width - img_width_pt) / 2
            y_pos = (page_height - img_height_pt) / 2

            pdf.drawImage(temp_image_path, x_pos, y_pos, img_width_pt, img_height_pt)
            os.remove(temp_image_path)

            pdf.save()
        return
    
    else:
        if not cover_path or not spine_path or not back_path:
            print("Cover, spine and back images must be named 'cover.png', 'spine.png' and 'back.png'.")
            return
        
        print("Resizing cover with three images...")
        
        images = ["cover/cover.png", "cover/spine.png", "cover/back.png"]
        if pages_order == "left":
            images.reverse()

        total_width_pt = 0
        image_dimensions = []
        counter = 0
        for image in images:
            with Image.open(image) as img:
                img_width, img_height = img.size
                aspect_ratio = img_width / img_height

                target_width_px = int(target_height_px * aspect_ratio)

                if image == "cover/spine.png":
                    target_width_px = img_width

                img = img.resize((target_width_px, target_height_px))

                temp_image_path = f"cover/temp_{counter}.png"
                img.save(temp_image_path, "PNG")

                img_width, img_height = img.size
                img_width_pt = pixels_to_points(img_width)
                img_height_pt = pixels_to_points(img_height)

                image_dimensions.append((img_width_pt, img_height_pt))

                total_width_pt += img_width_pt
                counter += 1

        x_start = (page_width - total_width_pt) // 2
        y_start = (page_height - image_dimensions[0][1]) // 2  

        images = ["cover/temp_0.png", "cover/temp_1.png", "cover/temp_2.png"]
        current_x = x_start
        for (image, (img_width_pt, img_height_pt)) in (zip(images, image_dimensions)):

            pdf.drawImage(image, current_x, y_start, width=img_width_pt, height=img_height_pt)

            current_x += img_width_pt

        pdf.save()

        for image in images:
            os.remove(image)

        print(f"Cover PDF created at {output_pdf}.")

def main():
    input_folder = "input"
    output_folder = "output"

    while True:
        choose_creation = input("Do you want to print a book (manga, comic, etc) or just a cover? (cover/book): ").strip().lower()
        if choose_creation in ["cover", "book"]:
            break
    
    if choose_creation == "book":
        welcome_message()
    else:
        welcome_message_cover()
            
    while True:
        pages_order = input("Choose the order in which you will be reading ('left to right' or 'right to left'): ").strip().lower()

        if pages_order == "left to right":
            pages_order = "left"
            break
        if pages_order == "right to left":
            pages_order = "right"
            break   
    while True:
        paper_size = input("Please choose paper size to print (A4, Letter, or A5): ").strip().upper()
        if paper_size in ["A4", "LETTER", "A5"]:
            break    

    if choose_creation == "book":
        while True:     
            delete_initial_pages = input("Delete ALL '000' pages? Usually the 000 pages are covers, artwork, fanmade, etc. (y/n): ").strip().lower()
            if delete_initial_pages == "y": 
                delete_initial_pages = True
                break
            elif delete_initial_pages == "n":
                delete_initial_pages = False
                break
        while True:
            manga_size = input("Please choose the width of the manga/book in centimeters (eg: 12.5) or type 'full' to cover the whole page: ").strip()
            if manga_size.isnumeric() and float(manga_size) > 0 and float(manga_size) <= 15: 
                manga_size = int(manga_size)
                break
            elif manga_size == "full":
                size = {
                    "A4": 15,
                    "Letter": 13,
                    "A5": 9,
                }
                manga_size = size[paper_size]
                break
    try:
        if choose_creation == "book":
            images_paths, double_page_paths, check = scan_and_sort_images(input_folder, manga_size, delete_initial_pages)
            create_pdf(images_paths, output_folder, paper_size, pages_order, double_page_paths, check)

            print(f"\nPDF saved in: {output_folder}\n")
            goodbye_message()
        else:
            create_cover(paper_size, output_folder, pages_order) 

        while True:   
            check = input("\nProcess finnished, do you want to delete everything in the input folder? Useful if you want to print again or change something (y/n): ").strip().lower()
            if check in ["y", "n"]:
                if check == "y":
                    for file in os.listdir(input_folder):
                        file_path = os.path.join(input_folder, file)
                        os.remove(file_path)
                    print("\nAll files in the input folder have been deleted.")
                break
        input("\nPress Enter to exit...")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()