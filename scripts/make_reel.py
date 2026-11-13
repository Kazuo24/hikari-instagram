"""Join a post's slide images into a short 9:16 slideshow video for a Reel.

Usage: python3 -I make_reel.py <out.mp4> <img1.jpg> [<img2.jpg> ...]
Each slide shows for about 4 seconds (8 seconds or more in total), padded onto
a 1080x1920 pink background. A silent audio track is added because some
players and the Reels uploader handle video-only files poorly.
"""
import subprocess, sys

BG = "0xFAE3E8"
PER = 4.0


def main():
    out, imgs = sys.argv[1], sys.argv[2:]
    per = max(PER, 8.0 / len(imgs))
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for i in imgs:
        cmd += ["-loop", "1", "-t", str(per), "-i", i]
    cmd += ["-f", "lavfi", "-t", str(per * len(imgs)), "-i", "anullsrc=r=44100:cl=stereo"]
    parts = "".join(
        f"[{k}:v]scale=1080:-2,pad=1080:1920:0:(oh-ih)/2:color={BG},setsar=1,fps=30[v{k}];"
        for k in range(len(imgs)))
    parts += "".join(f"[v{k}]" for k in range(len(imgs))) + f"concat=n={len(imgs)}:v=1:a=0[v]"
    cmd += ["-filter_complex", parts, "-map", "[v]", "-map", f"{len(imgs)}:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", "30",
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print("made", out)


if __name__ == "__main__":
    main()
