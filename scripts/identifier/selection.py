from pathlib import Path
import random

PARENT_DIR = Path(__file__).resolve().parent.parent.parent

IMAGE_DIR = PARENT_DIR / "data/resized_images"

def class_to_idx(directory):
    bird_dirs = sorted(d for d in directory.iterdir() if d.is_dir())

    selector = {}
    for index, bird_dir in enumerate(bird_dirs):
        if len(list(bird_dir.glob("*.jpg"))) == 0:
            print(bird_dir.name)
        selector[bird_dir.name] = index

    return selector

def match_image_paths_to_class(image_list, bird_directory, class_to_idx):
    class_no = class_to_idx[bird_directory.name]

    output_list = []
    for image_path in image_list:
        output_list.append((image_path, class_no))

    return output_list

def split_dataset(image_dir, class_to_idx, val_fraction=0.2):
    bird_dirs = sorted(d for d in image_dir.iterdir() if d.is_dir())
    train_samples = []
    val_samples = []

    for dir in bird_dirs:
        images = list(dir.glob("*.jpg"))
        random.shuffle(images)
        if images:
            path_class_pairs = match_image_paths_to_class(images, dir, class_to_idx)
            len_of_images = len(images)
        else:
            len_of_images = 0
        match len_of_images:
            case 0:
                continue
            case 1:
                train_samples.append(path_class_pairs[0])
            case 2:
                for index, image_class_pair in enumerate(path_class_pairs):
                    match index:
                        case 0:
                            train_samples.append(image_class_pair)
                        case 1:
                            val_samples.append(image_class_pair)
            case _:
                for index, image_class_pair in enumerate(path_class_pairs):
                    if index < round(len_of_images*val_fraction):
                        val_samples.append(image_class_pair)
                    else:
                        train_samples.append(image_class_pair)

    return val_samples, train_samples