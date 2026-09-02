"""
DROID / LeRobot dataset inspection tool.

Purpose:
    Inspect the actual contents of a GR00T demo dataset before running inference.

This script does NOT run GR00T.

It inspects:

    Dataset
        |
        +-- episode metadata
        +-- task / language
        +-- video streams
        |      |
        |      +-- decoded RGB frames
        |
        +-- Parquet data
               |
               +-- robot state
               +-- ground-truth action
               +-- other numerical fields

It also creates a visual inspection image showing:

    [camera image]

    timestep / frame information
    robot state
    ground-truth action

Important:
    The DROID action representation is NOT assumed to be the same
    as an SO-101 action representation.

    We inspect the modality metadata to determine what the values mean. 

Example usage: 
    python inspect_dataset.py --dataset /home/axonex/Documents/Isaac-GR00T/demo_data/droid_sample --episode 1 --output /home/axonex/Documents/Isaac-GR00T/playground_scripts/output
"""

from pathlib import Path
import json
import argparse

import cv2
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

DEFAULT_DATASET = Path(
    "/home/axonex/Documents/Isaac-GR00T/demo_data/droid_sample"
).expanduser()

DEFAULT_OUTPUT = Path(
    "/home/axonex/Documents/Isaac-GR00T/playground_scripts/output"
).expanduser()


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def print_header(title):
    """Print a visually distinct section header."""
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def print_subheader(title):
    """Print a smaller section header."""
    print()
    print("-" * 90)
    print(title)
    print("-" * 90)


def load_json(path):
    """Load a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def print_array_info(name, value):
    """
    Print useful information about a numerical value.

    Handles:
        numpy arrays
        lists
        scalars
        strings
    """

    print(f"\n{name}")

    print(f"  Python type : {type(value)}")

    if isinstance(value, np.ndarray):
        print(f"  shape       : {value.shape}")
        print(f"  dtype       : {value.dtype}")

        if value.size > 0:
            print(f"  min         : {np.min(value)}")
            print(f"  max         : {np.max(value)}")
            print(f"  mean        : {np.mean(value)}")
            print(f"  first values: {value.flatten()[:10]}")

    elif isinstance(value, (list, tuple)):
        print(f"  length      : {len(value)}")

        if len(value) > 0:
            print(f"  first values: {value[:10]}")

    else:
        print(f"  value       : {value}")


def convert_value(value):
    """
    Convert values from pandas / parquet into something
    convenient for inspection.
    """

    if isinstance(value, np.ndarray):
        return value

    if isinstance(value, list):
        return np.asarray(value)

    return value


# ---------------------------------------------------------------------
# Dataset structure
# ---------------------------------------------------------------------

def inspect_dataset_structure(dataset):
    """Print the files contained in the dataset."""

    print_header("DATASET STRUCTURE")

    for path in sorted(dataset.rglob("*")):
        if path.is_file():
            print(path.relative_to(dataset))


# ---------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------

def inspect_metadata(dataset):
    """Inspect the important LeRobot/DROID metadata files."""

    print_header("DATASET METADATA")

    meta = dataset / "meta"

    # -------------------------------------------------------------
    # info.json
    # -------------------------------------------------------------

    info_path = meta / "info.json"

    if info_path.exists():
        print_subheader("info.json")

        info = load_json(info_path)

        print(json.dumps(info, indent=2))

    # -------------------------------------------------------------
    # modality.json
    # -------------------------------------------------------------

    modality_path = meta / "modality.json"

    if modality_path.exists():
        print_subheader("modality.json")

        modality = load_json(modality_path)

        print(json.dumps(modality, indent=2))

    # -------------------------------------------------------------
    # tasks.jsonl
    # -------------------------------------------------------------

    tasks_path = meta / "tasks.jsonl"

    if tasks_path.exists():
        print_subheader("tasks.jsonl")

        with open(tasks_path, "r") as f:
            for line in f:
                print(line.rstrip())

    # -------------------------------------------------------------
    # episodes.jsonl
    # -------------------------------------------------------------

    episodes_path = meta / "episodes.jsonl"

    if episodes_path.exists():
        print_subheader("episodes.jsonl")

        with open(episodes_path, "r") as f:
            for line in f:
                print(line.rstrip())


# ---------------------------------------------------------------------
# Video inspection
# ---------------------------------------------------------------------

def inspect_video(video_path, output_dir, episode_name, stream_name):
    """
    Open a video with OpenCV and inspect the first frame.

    This is particularly useful because the user currently sees
    black videos in VLC.

    We check:

        - whether OpenCV can open the video
        - FPS
        - frame count
        - resolution
        - whether the first frame can be decoded
        - pixel statistics
        - percentage of nearly-black pixels

    The first frame is saved as PNG.
    """

    print_subheader(f"VIDEO: {stream_name}")

    print(f"Path: {video_path}")

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print("ERROR: OpenCV could NOT open this video.")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    print(f"FPS         : {fps}")
    print(f"Frame count : {frame_count}")
    print(f"Resolution  : {int(width)} x {int(height)}")

    ret, frame = cap.read()

    if not ret:
        print("ERROR: Video opened, but first frame could NOT be decoded.")
        cap.release()
        return None

    print(f"Decoded     : YES")
    print(f"Shape       : {frame.shape}")
    print(f"dtype       : {frame.dtype}")
    print(f"min pixel   : {frame.min()}")
    print(f"max pixel   : {frame.max()}")
    print(f"mean pixel  : {frame.mean():.3f}")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    black_ratio = np.mean(gray < 5)

    print(
        f"nearly black: {black_ratio * 100:.2f}%"
    )

    # -------------------------------------------------------------
    # Save first frame
    # -------------------------------------------------------------

    episode_dir = output_dir / episode_name
    episode_dir.mkdir(parents=True, exist_ok=True)

    safe_name = stream_name.replace("/", "_")

    frame_path = episode_dir / f"{safe_name}_frame000000.png"

    cv2.imwrite(str(frame_path), frame)

    print(f"Saved frame : {frame_path}")

    cap.release()

    return {
        "path": str(video_path),
        "fps": fps,
        "frame_count": frame_count,
        "width": int(width),
        "height": int(height),
        "frame": frame,
    }


# ---------------------------------------------------------------------
# Read all video streams for an episode
# ---------------------------------------------------------------------

def find_episode_videos(dataset, episode_id):
    """
    Find every MP4 belonging to the selected episode.

    Example:

        episode_000000.mp4

    may exist under:

        exterior camera
        wrist camera
        etc.
    """

    videos_dir = dataset / "videos"

    filename = f"episode_{episode_id:06d}.mp4"

    return sorted(videos_dir.rglob(filename))


# ---------------------------------------------------------------------
# Parquet inspection
# ---------------------------------------------------------------------

def inspect_parquet(parquet_path):
    """
    Inspect one DROID episode Parquet file.

    This tells us what numerical information actually exists.

    We deliberately do NOT call anything 'joint position',
    'gripper', 'velocity', etc. unless the dataset metadata says so.
    """

    print_header("PARQUET / ROBOT DATA")

    print(f"File: {parquet_path}")

    df = pd.read_parquet(parquet_path)

    print()
    print(f"Rows    : {len(df)}")
    print(f"Columns : {len(df.columns)}")

    print_subheader("COLUMN NAMES")

    for i, column in enumerate(df.columns):
        print(f"[{i:02d}] {column}")

    # -------------------------------------------------------------
    # Inspect first row
    # -------------------------------------------------------------

    print_subheader("FIRST ROW")

    first_row = df.iloc[0]

    for column in df.columns:

        value = convert_value(first_row[column])

        print_array_info(column, value)

    # -------------------------------------------------------------
    # Inspect a few rows
    # -------------------------------------------------------------

    print_subheader("FIRST 5 ROWS")

    print(df.head())

    return df


# ---------------------------------------------------------------------
# Numerical field classification
# ---------------------------------------------------------------------

def identify_candidate_fields(df):
    """
    Find likely state/action fields.

    This is intentionally heuristic.

    The actual meaning MUST be verified against modality.json.

    We don't assume that a column called 'action' has a particular
    dimension or ordering.
    """

    print_header("POSSIBLE STATE / ACTION FIELDS")

    columns = list(df.columns)

    for column in columns:

        lower = column.lower()

        if any(
            keyword in lower
            for keyword in [
                "action",
                "state",
                "observation.state",
                "robot",
                "joint",
                "gripper",
                "velocity",
                "position",
            ]
        ):
            print(f"Candidate: {column}")


# ---------------------------------------------------------------------
# Visual inspection
# ---------------------------------------------------------------------

def create_visual_inspection(
    frames,                 # dict[str, np.ndarray]  e.g. {"exterior_...": img, "wrist_...": img}
    episode_id,
    timestep,
    task,
    state_values,
    action_values,
    output_path,
):
    """
    Create a single inspection image that shows:
        - all camera views side-by-side
        - task / timestep
        - full robot state
        - full ground-truth action
    """

    # ------------------------------------------------------------------
    # Prepare camera images (keep original aspect, limit width)
    # ------------------------------------------------------------------
    max_cam_width = 480
    prepared = []

    for name, frame in frames.items():
        img = frame.copy()
        if img.shape[1] > max_cam_width:
            scale = max_cam_width / img.shape[1]
            img = cv2.resize(
                img,
                (int(img.shape[1] * scale), int(img.shape[0] * scale)),
            )
        # small label on the image itself
        cv2.putText(
            img, name, (8, 22),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1, cv2.LINE_AA,
        )
        prepared.append(img)

    # horizontal stack of cameras
    if not prepared:
        raise ValueError("No frames provided")
    cam_row = np.hstack(prepared) if len(prepared) > 1 else prepared[0]

    # ------------------------------------------------------------------
    # Build info panel – size it dynamically so nothing is truncated
    # ------------------------------------------------------------------
    panel_width = 520
    line_height = 26
    n_state = 0 if state_values is None else len(np.asarray(state_values).flatten())
    n_action = 0 if action_values is None else len(np.asarray(action_values).flatten())

    # headers + task lines + state + action + margins
    estimated_lines = 12 + n_state + n_action + 8
    panel_height = max(cam_row.shape[0], estimated_lines * line_height + 40)

    panel = np.zeros((panel_height, panel_width, 3), dtype=np.uint8)

    y = 32

    def write(text, size=0.55, color=(255, 255, 255)):
        nonlocal y
        cv2.putText(
            panel, text, (16, y),
            cv2.FONT_HERSHEY_SIMPLEX, size, color, 1, cv2.LINE_AA,
        )
        y += line_height

    # ---- basic info ----
    write(f"Episode : {episode_id}", 0.65)
    write(f"Timestep: {timestep}", 0.65)
    y += 8

    write("TASK", 0.65, (0, 200, 255))
    # simple word-wrap
    words = str(task).split()
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if len(test) > 42:
            write(line)
            line = w
        else:
            line = test
    if line:
        write(line)
    y += 12

    # ---- state ----
    write("ROBOT STATE", 0.65, (0, 255, 128))
    if state_values is None:
        write("Not found")
    else:
        state = np.asarray(state_values).flatten()
        write(f"shape = {state.shape}")
        for i, v in enumerate(state):
            write(f"state[{i:02d}] = {v:.6f}")
    y += 12

    # ---- action ----
    write("GROUND-TRUTH ACTION", 0.65, (255, 180, 0))
    if action_values is None:
        write("Not found")
    else:
        action = np.asarray(action_values).flatten()
        write(f"shape = {action.shape}")
        for i, v in enumerate(action):
            write(f"action[{i:02d}] = {v:.6f}")

    # ------------------------------------------------------------------
    # Final canvas: cameras on the left, panel on the right
    # ------------------------------------------------------------------
    height = max(cam_row.shape[0], panel.shape[0])
    canvas = np.zeros((height, cam_row.shape[1] + panel_width, 3), dtype=np.uint8)

    canvas[: cam_row.shape[0], : cam_row.shape[1]] = cam_row
    canvas[: panel.shape[0], cam_row.shape[1] :] = panel

    cv2.imwrite(str(output_path), canvas)
    print(f"\nVisual inspection saved to:\n  {output_path}")


# ---------------------------------------------------------------------
# Find likely state/action columns
# ---------------------------------------------------------------------

def find_column(df, candidates):
    """
    Find a column using a list of possible names.

    This does NOT guarantee semantic correctness.

    It is only used to make the inspector convenient.
    """

    for candidate in candidates:

        if candidate in df.columns:
            return candidate

    return None


# ---------------------------------------------------------------------
# Main inspection
# ---------------------------------------------------------------------

def inspect_episode(dataset, episode_id, output_dir):

    episode_name = f"episode_{episode_id:06d}"

    print_header(f"INSPECTING {episode_name}")

    # -------------------------------------------------------------
    # Locate Parquet
    # -------------------------------------------------------------

    parquet_files = sorted(
        (dataset / "data").rglob(
            f"{episode_name}.parquet"
        )
    )

    if not parquet_files:

        print("ERROR: Could not find Parquet file.")

        return

    parquet_path = parquet_files[0]

    # -------------------------------------------------------------
    # Read Parquet
    # -------------------------------------------------------------

    df = inspect_parquet(parquet_path)

    # -------------------------------------------------------------
    # Candidate fields
    # -------------------------------------------------------------

    identify_candidate_fields(df)

    # -------------------------------------------------------------
    # Find videos
    # -------------------------------------------------------------

    print_header("VIDEO STREAMS")

    videos = find_episode_videos(
        dataset,
        episode_id,
    )

    if not videos:

        print("No videos found.")

    video_results = {}

    for video_path in videos:

        # Convert:

        # observation.images.exterior_1_left

        # into a readable stream name.

        stream_name = video_path.parent.name

        result = inspect_video(
            video_path,
            output_dir,
            episode_name,
            stream_name,
        )

        if result is not None:
            video_results[stream_name] = result

    # -------------------------------------------------------------
    # Collect all decoded frames for visual inspection.
    # -------------------------------------------------------------

    if not video_results:
        print("\nNo decodable video frames found.")
        return

    frames = {
        name: result["frame"]
        for name, result in video_results.items()
    }

    # -------------------------------------------------------------
    # Determine task
    # -------------------------------------------------------------

    task = "UNKNOWN"

    # Prefer the task_index already present in the parquet row
    task_index = None
    if "task_index" in df.columns:
        task_index = int(df.iloc[0]["task_index"])

    if task_index is not None:
        tasks_path = dataset / "meta" / "tasks.jsonl"
        if tasks_path.exists():
            with open(tasks_path, "r") as f:
                for line in f:
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if item.get("task_index") == task_index:
                        task = item.get("task", "UNKNOWN")
                        break

    # -------------------------------------------------------------
    # Locate likely state/action fields.
    # -------------------------------------------------------------

    state_column = find_column(
        df,
        [
            "observation.state",
            "state",
            "observation.robot_state",
        ],
    )

    action_column = find_column(
        df,
        [
            "action",
            "actions",
        ],
    )

    # -------------------------------------------------------------
    # First timestep
    # -------------------------------------------------------------

    timestep = 0

    state_values = None
    action_values = None

    if state_column is not None:
        state_values = convert_value(
            df.iloc[timestep][state_column]
        )

    if action_column is not None:
        action_values = convert_value(
            df.iloc[timestep][action_column]
        )

    # -------------------------------------------------------------
    # Create visual inspection image.
    # -------------------------------------------------------------

    episode_output = (
        output_dir / episode_name
    )

    episode_output.mkdir(
        parents=True,
        exist_ok=True,
    )

    visual_path = (
        episode_output
        / "inspection_timestep_000000.png"
    )

    create_visual_inspection(
        frames=frames,
        episode_id=episode_id,
        timestep=timestep,
        task=task,
        state_values=state_values,
        action_values=action_values,
        output_path=visual_path,
    )

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------

    print_header("INSPECTION COMPLETE")

    print(f"Episode       : {episode_id}")
    print(f"Parquet       : {parquet_path}")
    print(f"Rows          : {len(df)}")

    print()
    print("Video streams:")

    for name, result in video_results.items():

        print(
            f"  {name}: "
            f"{result['width']}x{result['height']} "
            f"@ {result['fps']} FPS "
            f"({result['frame_count']} frames)"
        )

    print()
    print(f"State column  : {state_column}")
    print(f"Action column : {action_column}")

    print()
    print("IMPORTANT:")
    print(
        "The state/action dimension ordering has NOT been interpreted "
        "as an SO-101 robot representation."
    )

    print(
        "Use modality.json to determine the semantic meaning of "
        "each field."
    )


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Inspect a DROID / LeRobot dataset."
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to DROID dataset.",
    )

    parser.add_argument(
        "--episode",
        type=int,
        default=0,
        help="Episode number to inspect.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory for inspection images.",
    )

    args = parser.parse_args()

    dataset = args.dataset.expanduser()
    output = args.output.expanduser()

    if not dataset.exists():

        raise FileNotFoundError(
            f"Dataset does not exist: {dataset}"
        )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    inspect_dataset_structure(dataset)

    inspect_metadata(dataset)

    inspect_episode(
        dataset=dataset,
        episode_id=args.episode,
        output_dir=output,
    )


if __name__ == "__main__":
    main()
