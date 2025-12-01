import os
import face_recognition
import pickle
import cv2

def train_data(images_path="images", output_file="train.pkl"):
    """
    Trains face encodings from images in a folder and saves them to a pickle file.
    Each image filename should be the person's name (e.g., AHANA ROY.jpg).
    """
    known_encodings = []
    known_names = []

    if not os.path.exists(images_path):
        print(f"❌ Folder '{images_path}' not found.")
        return

    image_files = [f for f in os.listdir(images_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    if len(image_files) == 0:
        print(f"⚠️ No images found in '{images_path}' folder.")
        return

    print(f"🧠 Training started for {len(image_files)} image(s)...\n")

    for img_name in image_files:
        try:
            # Get name from filename (before extension)
            name = os.path.splitext(img_name)[0]

            # Load image and convert from BGR (OpenCV) to RGB (face_recognition expects RGB)
            img_path = os.path.join(images_path, img_name)
            image = cv2.imread(img_path)
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detect face locations and encodings
            boxes = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, boxes)

            if len(encodings) > 0:
                known_encodings.append(encodings[0])
                known_names.append(name)
                print(f"✅ Encoded: {name}")
            else:
                print(f"⚠️ No face found in {img_name}, skipping...")

        except Exception as e:
            print(f"❌ Error processing {img_name}: {e}")

    # Save the encodings and names to a pickle file
    if known_encodings:
        with open(output_file, "wb") as f:
            pickle.dump({"encodings": known_encodings, "names": known_names}, f)
        print(f"\n💾 Training complete! Encodings saved to '{output_file}'.")
    else:
        print("\n⚠️ No valid faces were encoded. Please check your images.")

# Example usage
if __name__ == "__main__":
    train_data()
