import cv2
import os

def capture_dataset(username):
    """
    Capture 10 cropped face images for a given student username.
    Each student's images are stored in dataset/<username>/
    """
    folder = os.path.join("dataset", username)
    os.makedirs(folder, exist_ok=True)

    # Haar Cascade for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("[ERROR] ❌ Could not access webcam.")
        return

    print(f"\n[INFO] Capturing faces for '{username}'.")
    print("[INFO] Press 'q' anytime to quit early.\n")

    count = 0
    while True:
        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))

        for (x, y, w, h) in faces:
            count += 1
            face = frame[y:y+h, x:x+w]
            save_path = os.path.join(folder, f"{count}.jpg")
            cv2.imwrite(save_path, face)

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"{username} - {count}/10", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            print(f"[✔] Saved {save_path}")

        cv2.imshow(f"Capturing Faces for {username}", frame)

        # Stop when 10 images saved or 'q' pressed
        if cv2.waitKey(1) & 0xFF == ord('q') or count >= 10:
            break

    cam.release()
    cv2.destroyAllWindows()
    print(f"[✅] Done capturing {count} images for {username}.\n")


def capture_for_multiple_students():
    """
    Capture datasets for multiple students — asks for username each time.
    """
    print("=== Student Face Dataset Capture ===")
    print("Type 'exit' to stop capturing for new students.\n")

    while True:
        username = input("Enter student username: ").strip()
        if not username:
            print("⚠️ Username cannot be empty.\n")
            continue
        if username.lower() == "exit":
            print("\n[INFO] Exiting dataset capture tool.")
            break

        capture_dataset(username)


if __name__ == "__main__":
    capture_for_multiple_students()
