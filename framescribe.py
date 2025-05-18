import os
import shutil
import subprocess
import re
import math
import platform
from datetime import timedelta
from pathlib import Path

try:
    import cv2  # OpenCV
    from PIL import Image
    from fpdf import FPDF
except ImportError:
    print(
        "Missing required libraries. Please install them using:\n"
        "pip install opencv-python Pillow fpdf2 yt-dlp"
    )
    exit(1)

# --- Configuration ---
TARGET_PDF_SIZE_MB = 8
COMPRESSED_IMAGE_QUALITY = 75  # JPEG quality for compression (0-100)
TEMP_FRAME_DIR_NAME = "temp_frames"


def sanitize_filename(name):
    """Removes invalid characters for filenames/directory names."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def get_video_info_and_download(youtube_url, base_output_dir):
    """
    Downloads video, audio, subtitles using yt-dlp and gets video info.
    Returns (title, video_path, srt_path, duration_seconds) or None on failure.
    """
    print(f"Attempting to download: {youtube_url}")
    try:
        # Get video title first to create the specific output directory
        result = subprocess.run(
            ["yt-dlp", "--get-title", "--get-duration", youtube_url],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        lines = result.stdout.strip().split("\n")
        video_title_raw = lines[0]
        duration_str = lines[1]

        # Parse duration (e.g., HH:MM:SS or MM:SS or SS)
        parts = list(map(int, duration_str.split(":")))
        if len(parts) == 3:
            duration_seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            duration_seconds = parts[0] * 60 + parts[1]
        else:
            duration_seconds = parts[0]

        video_title_sanitized = sanitize_filename(video_title_raw)
        specific_output_dir = base_output_dir / video_title_sanitized
        os.makedirs(specific_output_dir, exist_ok=True)
        print(f"Video title: {video_title_raw}")
        print(f"Output will be in: {specific_output_dir}")

        # Download video, audio (merged), and subtitles
        # Format: best video (mp4) + best audio (m4a) / best (mp4 if already merged)
        # Write auto-generated subs if available, convert to srt
        yt_dlp_command = [
            "yt-dlp",
            "-f",
            "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
            "--write-auto-subs",
            "--sub-format",
            "srt",
            "--convert-subs",
            "srt",
            "-o",
            str(specific_output_dir / "%(title)s.%(ext)s"),
            youtube_url,
        ]

        print(f"Running yt-dlp: {' '.join(yt_dlp_command)}")
        process = subprocess.Popen(
            yt_dlp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            print("yt-dlp Error:")
            print(stdout.decode(errors="ignore"))
            print(stderr.decode(errors="ignore"))
            return None, None, None, 0

        print("Download process finished.")

        # Find the downloaded video and srt files
        video_path = None
        srt_path = None
        for item in specific_output_dir.iterdir():
            if item.is_file():
                # yt-dlp might add language code to srt, e.g., title.en.srt
                if item.suffix == ".mp4": # Common video format
                    video_path = item
                elif item.suffix == ".srt":
                    srt_path = item
                elif item.suffix == ".mkv": # Another common video format
                    video_path = item


        if not video_path:
            print("Could not find downloaded video file (.mp4 or .mkv).")
            # Try to find any video file if mp4/mkv not found
            for ext in [".webm", ".flv", ".avi", ".mov"]:
                 for item in specific_output_dir.iterdir():
                    if item.suffix == ext:
                        video_path = item
                        print(f"Found video with extension {ext}")
                        break
                 if video_path:
                     break
            if not video_path:
                print("Still no video file found. Check download output.")
                return None, None, None, 0


        if srt_path:
            print(f"Found transcript: {srt_path.name}")
        else:
            print("No SRT transcript found/downloaded.")

        return (
            video_title_sanitized,
            video_path,
            srt_path,
            duration_seconds,
            specific_output_dir,
        )

    except subprocess.CalledProcessError as e:
        print(f"Error getting video info with yt-dlp: {e}")
        print(e.stderr)
        return None, None, None, 0, None
    except FileNotFoundError:
        print(
            "Error: yt-dlp command not found. Is it installed and in your PATH?"
        )
        return None, None, None, 0, None
    except Exception as e:
        print(f"An unexpected error occurred during download: {e}")
        return None, None, None, 0, None


def get_frame_extraction_interval(video_duration_seconds):
    """Asks user for frame extraction interval and confirms."""
    while True:
        try:
            interval_str = input(
                "Extract one frame every how many seconds (e.g., 2, 0.5)? "
            )
            interval_seconds = float(interval_str)
            if interval_seconds <= 0:
                print("Interval must be positive.")
                continue

            num_frames = math.floor(video_duration_seconds / interval_seconds)
            if num_frames == 0 and video_duration_seconds > 0:
                num_frames = 1 # Ensure at least one frame for short videos
            print(
                f"This will extract approximately {num_frames} frames."
            )
            confirm = (
                input("Proceed? (y/n, or 'c' to change interval): ")
                .strip()
                .lower()
            )
            if confirm == "y":
                return interval_seconds, num_frames
            elif confirm == "c":
                continue
            else:
                print("Frame extraction cancelled by user.")
                return None, 0
        except ValueError:
            print("Invalid input. Please enter a number.")


def format_timestamp(seconds):
    """Formats seconds into HH:MM:SS.mmm string."""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds_val = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{seconds_val:02}.{milliseconds:03}"


def extract_frames(
    video_path, interval_seconds, num_expected_frames, output_folder
):
    """Extracts frames from video and saves them with timestamped names."""
    print(f"Extracting frames from {video_path.name}...")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        print("Warning: Video FPS is 0. Cannot extract frames accurately by time.")
        # Fallback: try to use num_expected_frames if interval was based on duration
        total_frames_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if num_expected_frames > 0 and total_frames_video > 0:
            frame_step = max(1, total_frames_video // num_expected_frames)
            print(f"Using fallback frame step: {frame_step}")
        else:
            cap.release()
            return [] # Cannot proceed
    else:
        frame_step = int(fps * interval_seconds)
        if frame_step == 0: # for very small intervals and low fps
            frame_step = 1


    frame_data = []  # List of (frame_path, timestamp_str)

    temp_frames_path = output_folder / TEMP_FRAME_DIR_NAME
    os.makedirs(temp_frames_path, exist_ok=True)

    frame_count = 0
    saved_frame_count = 0
    success = True

    while success:
        if frame_count % frame_step == 0:
            success, image = cap.read()
            if success:
                current_time_seconds = frame_count / fps if fps > 0 else 0
                timestamp_str = format_timestamp(current_time_seconds)
                frame_filename = f"frame_{timestamp_str.replace(':', '-').replace('.', '_')}.jpg"
                frame_filepath = temp_frames_path / frame_filename

                cv2.imwrite(str(frame_filepath), image)
                frame_data.append((frame_filepath, timestamp_str))
                saved_frame_count += 1
                print(f"Saved frame {saved_frame_count} at {timestamp_str}")
            else:
                break # No more frames or error
        else:
            # Skip frame to maintain interval, but still need to read it
            success = cap.grab()
            if not success:
                break

        frame_count += 1
        if saved_frame_count >= num_expected_frames * 2 and num_expected_frames > 0 : # Safety break
            print("Warning: Extracted significantly more frames than expected. Stopping.")
            break


    cap.release()
    print(f"Finished extracting {saved_frame_count} frames.")
    return frame_data


def create_pdf_from_frames(
    frame_data, output_pdf_path, compress_mode=False
):
    """Creates a PDF from frame images, optionally compressing them."""
    print(f"Creating PDF: {output_pdf_path.name}...")
    pdf = FPDF(orientation="L", unit="mm", format="A4") # Landscape A4
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=10)

    # A4 Landscape dimensions in mm: 297 wide x 210 high
    # Margins (approximate, can be adjusted)
    margin_x = 10
    margin_y = 10
    page_width_mm = pdf.w - 2 * margin_x
    page_height_mm = pdf.h - 2 * margin_y

    for frame_path, timestamp_str in frame_data:
        try:
            img = Image.open(frame_path)
            img_w_px, img_h_px = img.size

            # Calculate image dimensions to fit page while maintaining aspect ratio
            aspect_ratio = img_w_px / img_h_px
            
            display_w_mm = page_width_mm
            display_h_mm = display_w_mm / aspect_ratio

            if display_h_mm > page_height_mm:
                display_h_mm = page_height_mm
                display_w_mm = display_h_mm * aspect_ratio
            
            # Center image
            pos_x = (pdf.w - display_w_mm) / 2
            pos_y = (pdf.h - display_h_mm - 10) / 2 # Extra 10mm for timestamp

            pdf.add_page()

            if compress_mode:
                # Save to a temporary compressed file before adding to PDF
                temp_compressed_path = frame_path.with_suffix(
                    ".compressed.jpg"
                )
                img.save(
                    temp_compressed_path,
                    "JPEG",
                    quality=COMPRESSED_IMAGE_QUALITY,
                    optimize=True
                )
                pdf.image(
                    str(temp_compressed_path),
                    x=pos_x,
                    y=pos_y,
                    w=display_w_mm,
                    h=display_h_mm,
                )
                os.remove(temp_compressed_path) # Clean up temp compressed
            else:
                pdf.image(
                    str(frame_path),
                    x=pos_x,
                    y=pos_y,
                    w=display_w_mm,
                    h=display_h_mm,
                )
            
            # Add timestamp
            pdf.set_xy(pos_x, pos_y + display_h_mm + 2) # Position below image
            pdf.cell(display_w_mm, 8, txt=timestamp_str, ln=1, align="C")

        except Exception as e:
            print(f"Error processing frame {frame_path.name} for PDF: {e}")
            continue # Skip problematic frame

    pdf.output(str(output_pdf_path), "F")
    print("PDF created successfully.")


def open_folder(folder_path):
    """Opens the specified folder in the system's file explorer."""
    try:
        if platform.system() == "Windows":
            os.startfile(str(folder_path))
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", str(folder_path)], check=True)
        else:  # Linux and other Unix-like
            subprocess.run(["xdg-open", str(folder_path)], check=True)
        print(f"Opened output folder: {folder_path}")
    except Exception as e:
        print(f"Could not open folder {folder_path}: {e}")
        print("Please navigate to it manually.")


def main():
    script_dir = Path(__file__).parent.resolve()
    print(f"Script running in: {script_dir}")

    youtube_url = input("Enter YouTube video URL: ").strip()
    if not youtube_url:
        print("No URL entered. Exiting.")
        return

    (
        video_title,
        video_path,
        srt_path,
        duration_seconds,
        output_dir,
    ) = get_video_info_and_download(youtube_url, script_dir)

    if not video_title or not video_path or not output_dir:
        print("Failed to download or get video info. Exiting.")
        return

    if duration_seconds == 0 and video_path: # Try to get duration via OpenCV if yt-dlp failed for it
        try:
            cap_temp = cv2.VideoCapture(str(video_path))
            if cap_temp.isOpened():
                fps_temp = cap_temp.get(cv2.CAP_PROP_FPS)
                total_frames_temp = cap_temp.get(cv2.CAP_PROP_FRAME_COUNT)
                if fps_temp > 0 and total_frames_temp > 0:
                    duration_seconds = total_frames_temp / fps_temp
                    print(f"Retrieved duration via OpenCV: {duration_seconds:.2f}s")
            cap_temp.release()
        except Exception as e:
            print(f"Could not get duration via OpenCV: {e}")


    if duration_seconds == 0:
        print("Could not determine video duration. Cannot proceed with timed frame extraction.")
        # Clean up downloaded video if it exists
        if video_path and video_path.exists():
            print(f"Deleting downloaded video: {video_path.name}")
            video_path.unlink()
        if srt_path and srt_path.exists(): # srt_path is already in output_dir
            pass # Keep srt if user wants it
        # shutil.rmtree(output_dir) # Don't delete if srt is there
        return

    print(f"Video Duration: {timedelta(seconds=int(duration_seconds))}")

    interval_seconds, num_expected_frames = get_frame_extraction_interval(
        duration_seconds
    )
    if interval_seconds is None:
        # User cancelled, but video and srt might be downloaded.
        # We'll keep them in the folder.
        print("Exiting as per user request.")
        if video_path and video_path.exists():
            print(f"Downloaded video kept at: {video_path}")
        if srt_path and srt_path.exists():
            print(f"Transcript kept at: {srt_path}")
        open_folder(output_dir)
        return

    frame_data = extract_frames(
        video_path, interval_seconds, num_expected_frames, output_dir
    )
    if not frame_data:
        print("No frames were extracted. Exiting.")
        # Clean up video, keep srt
        if video_path and video_path.exists():
            print(f"Deleting downloaded video: {video_path.name}")
            video_path.unlink()
        open_folder(output_dir)
        return

    pdf_filename = f"{video_title}_frames.pdf"
    output_pdf_path = output_dir / pdf_filename
    compressed_pdf_path = output_dir / f"{video_title}_frames_compressed.pdf"

    # Initial PDF creation (uncompressed)
    create_pdf_from_frames(frame_data, output_pdf_path, compress_mode=False)
    final_pdf_path = output_pdf_path

    if output_pdf_path.exists():
        compress_choice = (
            input("Do you want to try to compress the PDF (e.g., under 8MB)? (y/n): ")
            .strip()
            .lower()
        )
        if compress_choice == "y":
            print(
                f"Attempting to compress PDF by reducing image quality to {COMPRESSED_IMAGE_QUALITY}%..."
            )
            create_pdf_from_frames(
                frame_data, compressed_pdf_path, compress_mode=True
            )
            if compressed_pdf_path.exists():
                original_size = output_pdf_path.stat().st_size
                compressed_size = compressed_pdf_path.stat().st_size
                print(
                    f"Original PDF size: {original_size / (1024*1024):.2f} MB"
                )
                print(
                    f"Compressed PDF size: {compressed_size / (1024*1024):.2f} MB"
                )

                if compressed_size < TARGET_PDF_SIZE_MB * 1024 * 1024:
                    print(
                        f"Compressed PDF is under {TARGET_PDF_SIZE_MB}MB."
                    )
                    # Delete uncompressed, use compressed
                    output_pdf_path.unlink()
                    final_pdf_path = compressed_pdf_path
                elif compressed_size < original_size:
                    print(
                        "Compression reduced size, but may still be over target."
                    )
                    # Ask user which one to keep
                    keep_compressed = input(
                        f"Compressed PDF is {compressed_size / (1024*1024):.2f}MB. Keep compressed version? (y/n): "
                    ).strip().lower()
                    if keep_compressed == 'y':
                        output_pdf_path.unlink()
                        final_pdf_path = compressed_pdf_path
                    else:
                        compressed_pdf_path.unlink()
                        final_pdf_path = output_pdf_path # Keep original
                else:
                    print(
                        "Compression did not reduce size or failed. Keeping original."
                    )
                    if compressed_pdf_path.exists():
                        compressed_pdf_path.unlink() # Delete ineffective compressed version
                    final_pdf_path = output_pdf_path
            else:
                print("Compression attempt failed. Keeping original PDF.")
        else:
            print("Skipping PDF compression.")
    else:
        print("PDF creation failed. No PDF to compress.")

    # Clean up temporary frame images
    temp_frames_full_path = output_dir / TEMP_FRAME_DIR_NAME
    if temp_frames_full_path.exists():
        print(f"Deleting temporary frames from: {temp_frames_full_path}")
        shutil.rmtree(temp_frames_full_path)

    # Delete original video file
    if video_path and video_path.exists():
        print(f"Deleting downloaded video file: {video_path.name}")
        video_path.unlink()
    else:
        print("Video file already deleted or was not found.")

    print("\n--- Process Complete ---")
    if final_pdf_path.exists():
        print(f"PDF with frames: {final_pdf_path}")
    if srt_path and srt_path.exists():
        print(f"Transcript: {srt_path}")
    elif not srt_path:
        print("Transcript: Not available or not downloaded.")
    
    print(f"All outputs are in folder: {output_dir}")
    open_folder(output_dir)


if __name__ == "__main__":
    main()

