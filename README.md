# FrameScribe: YouTube Video to PDF Frames & Transcript

**FrameScribe extracts timestamped frames into a PDF and a transcript from any YouTube video.**

This Python script allows you to download a YouTube video, extract its subtitles as a transcript, select frames from the video at specified intervals, and compile those frames into a PDF document. Both the PDF frames and the transcript include timestamps.

## Features

-   **Video Download:** Downloads the YouTube video in the best available quality (MP4 format preferred, merging best video and audio).
-   **Transcript Extraction:** Downloads available subtitles (preferably auto-generated if manual ones aren't present) and converts them to SRT format, which includes timestamps.
-   **Custom Frame Extraction:**
    -   Prompts the user to specify the interval (in seconds) for frame extraction (e.g., every 2 seconds, every 0.5 seconds).
    -   Displays the total estimated number of frames before proceeding, allowing the user to adjust the interval.
-   **PDF Generation:**
    -   Compiles the extracted frames into a PDF document.
    -   Each frame in the PDF is accompanied by its corresponding timestamp from the video.
-   **Optional PDF Compression:**
    -   Asks the user if they want to attempt to compress the PDF to be under a target size (default 8MB).
    -   Compression is achieved by reducing JPEG quality of the frames.
-   **Organized Output:**
    -   Creates a new folder named after the video title in the same directory as the script.
    -   Saves the final PDF and the SRT transcript file in this folder.
-   **Automatic Cleanup:** Deletes the downloaded video file and temporary frame images after processing.
-   **Folder Auto-Open:** Attempts to open the output folder in the system's file explorer upon completion.

## Prerequisites

Before running the script, ensure you have the following installed:

1.  **Python 3.7+**: Download from [python.org](https://www.python.org/downloads/).
2.  **`yt-dlp`**: A powerful command-line program to download videos from YouTube and other sites.
    -   Installation: `pip install yt-dlp`
    -   Alternatively, see [yt-dlp installation instructions](https://github.com/yt-dlp/yt-dlp#installation) for other methods (e.g., package managers).
3.  **FFmpeg**: `yt-dlp` requires FFmpeg to download and merge separate video and audio streams (common for high-quality YouTube downloads) and for some format conversions. OpenCV also benefits from it.
    -   Download from [ffmpeg.org](https://ffmpeg.org/download.html).
    -   **Crucial:** Add the `bin` directory of your FFmpeg installation to your system's PATH environment variable.
4.  **Python Libraries**: These will be installed via `requirements.txt`.

## Installation

1.  **Clone the repository or download the script:**
    If this were a Git repository:
    ```bash
    git clone https://github.com/Microck/FrameScribe
    cd FrameScribe
    ```
    Otherwise, just download `framescribe.py` and `requirements.txt` into a new folder.

2.  **Install FFmpeg:**
    -   Download FFmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html).
    -   Extract it to a suitable location (e.g., `C:\ffmpeg` on Windows or `/usr/local/ffmpeg` on Linux/macOS).
    -   Add the `bin` subdirectory (e.g., `C:\ffmpeg\bin`) to your system's PATH environment variable. You can verify by opening a new terminal and typing `ffmpeg -version`.

3.  **Install Python dependencies:**
    Navigate to the directory containing `framescribe.py` and `requirements.txt`, then run:
    ```bash
    pip install -r requirements.txt
    ```

## How to Use

1.  **Open a terminal or command prompt.**
2.  **Navigate to the directory** where you saved `framescribe.py`.
    ```bash
    cd path/to/your/script_directory
    ```
3.  **Run the script:**
    ```bash
    python framescribe.py
    ```
4.  **Follow the on-screen prompts:**
    *   **Enter YouTube video URL:** Paste the full URL of the YouTube video you want to process.
    *   **Frame extraction interval:** Enter the number of seconds between frame captures (e.g., `2` for a frame every 2 seconds, `0.5` for two frames per second). The script will show an estimated total number of frames. You can confirm or change the interval.
    *   **PDF Compression:** After the initial PDF is created, you'll be asked if you want to attempt to compress it.

## Output

Upon successful completion, the script will:

1.  Create a new folder in the script's directory, named after the sanitized title of the YouTube video (e.g., `My Awesome Video Title`).
2.  Inside this folder, you will find:
    *   **`VIDEO_TITLE_frames.pdf`** (or `VIDEO_TITLE_frames_compressed.pdf`): The PDF file containing the extracted video frames. Each frame will have its corresponding video timestamp (e.g., `HH:MM:SS.mmm`) printed below it.
    *   **`VIDEO_TITLE.en.srt`** (or similar, depending on the language): The transcript file in SRT format. SRT files inherently contain start and end timestamps for each line of dialogue.
3.  The original downloaded video file (`.mp4`, `.mkv`, etc.) and any temporary frame image files will be automatically deleted.
4.  The script will attempt to open the output folder for you.

## Configuration (Inside the Script)

You can modify these constants at the beginning of the `framescribe.py` script if needed:

-   `TARGET_PDF_SIZE_MB = 8`: The target size in megabytes for PDF compression.
-   `COMPRESSED_IMAGE_QUALITY = 75`: The JPEG quality (0-100) used when compressing frames for the PDF. Lower values mean smaller size but lower quality.
-   `TEMP_FRAME_DIR_NAME = "temp_frames"`: Name of the temporary directory for storing frames before PDF creation.

## Troubleshooting & Notes

-   **`yt-dlp` errors:** YouTube often changes its site structure, which can break downloaders. If you encounter issues with downloading, try updating `yt-dlp`:
    ```bash
    pip install --upgrade yt-dlp
    ```
-   **FFmpeg not found:** If the script reports it cannot find FFmpeg, ensure it's installed correctly and its `bin` directory is in your system's PATH. You might need to restart your terminal or even your computer after modifying the PATH.
-   **Long processing times:** For very long videos or very small frame extraction intervals, the script can take a considerable amount of time and consume significant disk space temporarily.
-   **Subtitle availability:** The script attempts to download auto-generated subtitles if official ones aren't available. If no subtitles exist for the video, no transcript file will be produced.
-   **PDF compression:** The compression feature reduces image quality to shrink file size. It's a "best effort" and might not always achieve the target size, especially if there are many high-resolution frames.
-   **Video formats:** `yt-dlp` usually downloads in MP4 or MKV. The script is primarily tested with these.
-   **Permissions:** Ensure the script has write permissions in the directory where it's located to create folders and files.

---
