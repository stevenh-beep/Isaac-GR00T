Yes. Let's make this much more concrete and **much smaller than a full Isaac Lab + GR00T system**.

One important correction first: there is not a simple "DROID robot" asset that you can just select in Isaac Sim and then use with GR00T. **DROID is a real robot/data embodiment used by GR00T**, with two camera streams and a particular state/action representation. For your simulation, the sensible first step is to build a **DROID-like simulation using a Franka/Panda**, with the same two-camera structure and compatible data fields. NVIDIA's current GR00T documentation explicitly defines the DROID inputs as `exterior_image_1_left`, `wrist_image_left`, `eef_9d`, `gripper_position`, `joint_position`, and language; the DROID action has the same 9+1+7 structure. ([GitHub][1])

Also, GR00T's current API expects batched arrays shaped `(B,T,...)`, RGB `uint8` images, `float32` states, and returns action arrays shaped `(B,T,D)`. ([GitHub][2])

So I recommend this exact progression:

```text
STEP 1
Isaac Sim UI
    ↓
Franka + gripper + 2 cameras
    ↓
save USD

STEP 2
Python
    ↓
load USD
    ↓
simulate
    ↓
capture:
    images
    joint state
    EEF pose
    gripper
    ↓
save locally

STEP 3
Python
    ↓
raw recording
    ↓
DROID/GR00T observation format

STEP 4
Python
    ↓
GR00T
    ↓
predicted action
    ↓
save/print action

STEP 5
Python
    ↓
GR00T action
    ↓
convert to Franka command
    ↓
Isaac Sim
    ↓
Franka moves
```

I would **not start with Isaac Lab integration yet**. First make this work with a normal Isaac Sim USD scene. Once that works, moving the exact same observation/action bridge into Isaac Lab becomes much easier.

---

# 0. What we are going to build

At the end, your directory will look approximately like:

```text
~/groot-poc/
├── isaac_droid_sim/
│   ├── inspect_scene.py
│   ├── record_droid.py
│   ├── prepare_groot.py
│   ├── run_groot.py
│   └── replay_groot_action.py
│
├── droid_scene/
│   └── franka_droid_scene.usd
│
└── data/
    └── droid_sim/
        └── episode_000/
            ├── images/
            │   ├── exterior/
            │   │   ├── 000000.png
            │   │   ├── 000001.png
            │   │   └── ...
            │   └── wrist/
            │       ├── 000000.png
            │       └── ...
            │
            ├── state/
            │   ├── 000000.npz
            │   ├── 000001.npz
            │   └── ...
            │
            └── metadata.json
```

Then:

```text
recorded data
      ↓
prepare_groot.py
      ↓
GR00T observation
      ↓
run_groot.py
      ↓
GR00T action
      ↓
replay_groot_action.py
      ↓
Isaac Sim
```

---

# 1. Create the DROID-like scene in Isaac Sim

## 1.1 Start Isaac Sim normally

Open Isaac Sim the way you have been using it.

Do **not** start Isaac Lab yet.

We want a simple Isaac Sim scene first.

---

# 1.2 Create a new empty stage

In Isaac Sim:

**File → New**

You should have an empty stage.

---

# 1.3 Add a ground plane

Use:

**Create → Physics → Ground Plane**

You should now have:

```text
World
└── GroundPlane
```

---

# 1.4 Add the Franka

Use Isaac Sim's asset browser/content browser.

Search for:

```text
Franka
```

Choose the Franka Panda asset you previously used.

Place it approximately:

```text
X = 0
Y = 0
Z = 0
```

The exact position isn't important.

You should see:

```text
Franka
   │
   ├── arm
   └── gripper
```

---

# 1.5 Make sure the Franka is an articulated robot

Select the Franka in the Stage panel.

You should be able to see its joints / articulation structure.

For this experiment, you need:

```text
7 arm joints
+
gripper
```

Don't worry about exact joint names yet.

---

# 1.6 Add an object for the robot to look at

For example:

**Create → Mesh → Cube**

Put the cube approximately:

```text
X = 0.5
Y = 0
Z = 0.05
```

Scale it to something obvious, e.g.:

```text
0.05 × 0.05 × 0.05 m
```

This is just a visual target.

Don't try to make GR00T successfully pick it up yet.

---

# 1.7 Add the exterior camera

Create:

**Create → Camera**

Place it to the left/front of the robot.

For example, conceptually:

```text
             camera
               \
                \
                 \
             Franka
               |
               |
             cube
```

You want the camera to see:

* the whole Franka
* gripper
* workspace
* cube

This will become:

```text
exterior_image_1_left
```

---

# 1.8 Rename the camera

This is important.

In the Stage panel, rename the camera:

```text
exterior_camera
```

So your scene should contain something similar to:

```text
World
├── Franka
├── GroundPlane
├── Cube
└── exterior_camera
```

The exact hierarchy may differ.

---

# 1.9 Add the wrist camera

Now create another camera:

**Create → Camera**

This time put it on/near the Franka wrist/hand.

You want approximately:

```text
                wrist camera
                    ↓
              ┌──────────┐
              │ gripper  │
              └──────────┘
                   |
                 Franka
```

The camera should see approximately what a camera mounted near the wrist would see.

It does **not** need to be perfectly calibrated yet.

---

# 1.10 Rename it

Rename it:

```text
wrist_camera
```

Your scene should now have:

```text
World
├── Franka
├── GroundPlane
├── Cube
├── exterior_camera
└── wrist_camera
```

---

# 1.11 Important: actually parent the wrist camera

This is the first place where the UI is useful.

In the Stage tree, ideally you want:

```text
Franka
├── ...
└── panda_hand
    └── wrist_camera
```

or whatever the corresponding hand/wrist prim is called in your Franka asset.

The critical point is:

> The wrist camera must be a child of a moving Franka link.

Otherwise it is just a camera sitting near the robot.

If you move the Franka and the camera stays in place, it is wrong.

---

# 1.12 Test the wrist camera

Move the Franka using the Isaac Sim UI.

For example, change one joint.

Watch the wrist camera.

It should move with the robot.

You want:

```text
move arm
   ↓
wrist camera moves
```

not:

```text
move arm
   ↓
wrist camera stays fixed
```

---

# 1.13 Save the USD

Now:

**File → Save As**

Create:

```text
~/groot-poc/droid_scene/franka_droid_scene.usd
```

You can create the directory first:

```bash
mkdir -p ~/groot-poc/droid_scene
```

The important thing is that **you now have a reproducible USD scene**.

---

# 1.14 Do NOT worry about perfect DROID geometry

At this stage:

```text
Franka + gripper
       +
external camera
       +
wrist camera
       +
workspace/object
```

is enough.

We are building the software pipeline first.

---

# 2. Inspect the USD scene with Python

Before recording anything, we need to discover the actual prim paths.

This is important because I don't want to tell you:

```text
/World/Franka/panda_hand
```

if your actual USD contains:

```text
/World/Franka/robot/panda_hand
```

or something else.

Create:

```bash
mkdir -p ~/groot-poc/isaac_droid_sim
cd ~/groot-poc/isaac_droid_sim
nano inspect_scene.py
```

Put this in it:

```python
from isaacsim import SimulationApp

# Start Isaac Sim.
simulation_app = SimulationApp({
    "headless": False,
})

import omni.usd


USD_PATH = "/home/YOUR_USERNAME/groot-poc/droid_scene/franka_droid_scene.usd"


# Load the USD scene.
omni.usd.get_context().open_stage(USD_PATH)

stage = omni.usd.get_context().get_stage()

print("\n" + "=" * 80)
print("USD STAGE")
print("=" * 80)

for prim in stage.Traverse():
    path = prim.GetPath()
    prim_type = prim.GetTypeName()

    print(f"{path}    [{prim_type}]")

print("\n" + "=" * 80)
print("END")
print("=" * 80)

# Keep Isaac Sim open.
while simulation_app.is_running():
    simulation_app.update()

simulation_app.close()
```

Replace:

```python
/home/YOUR_USERNAME/
```

with your actual home directory.

You can check it with:

```bash
echo $HOME
```

---

# 2.1 Run it

Use Isaac Sim's Python executable.

If your Isaac Sim installation is under the normal location, this is typically:

```bash
~/isaacsim/python.sh ~/groot-poc/isaac_droid_sim/inspect_scene.py
```

If your installation is somewhere else, use its `python.sh`.

---

# 2.2 What you are looking for

The terminal will print things like:

```text
/World
/World/Franka
/World/Franka/panda_link0
/World/Franka/panda_link1
...
/World/Franka/panda_hand
/World/Franka/panda_hand/wrist_camera
/World/exterior_camera
/World/GroundPlane
/World/Cube
```

Save that output.

**This gives us the exact paths needed by the recorder.**

---

# 3. Record the robot + cameras

Now we make the first useful Python program.

The program will:

```text
load USD
   ↓
start simulation
   ↓
find robot
   ↓
find cameras
   ↓
step simulation
   ↓
capture:
   camera image
   joint positions
   joint velocities
   EEF pose
   gripper
   ↓
save to disk
```

---

# 3.1 First install/check Python dependencies

In your Isaac Sim environment:

```bash
~/isaacsim/python.sh -c "import numpy; import PIL; print('OK')"
```

If that prints:

```text
OK
```

we're fine.

---

# 3.2 Create recorder

```bash
nano ~/groot-poc/isaac_droid_sim/record_droid.py
```

Use this initial recorder:

```python
from isaacsim import SimulationApp

simulation_app = SimulationApp({
    "headless": False,
})

import json
from pathlib import Path

import numpy as np
from PIL import Image

import omni.usd
from pxr import UsdGeom

from isaacsim.core.api import World
from isaacsim.core.prims import Articulation
from isaacsim.sensors.camera import Camera


# ============================================================
# USER SETTINGS
# ============================================================

USD_PATH = "/home/YOUR_USERNAME/groot-poc/droid_scene/franka_droid_scene.usd"

ROBOT_PRIM = "/World/Franka"
EXTERIOR_CAMERA_PRIM = "/World/exterior_camera"
WRIST_CAMERA_PRIM = "/World/Franka/panda_hand/wrist_camera"

OUTPUT_DIR = Path(
    "/home/YOUR_USERNAME/groot-poc/data/droid_sim/episode_000"
)

NUM_FRAMES = 100

# Camera recording resolution.
WIDTH = 320
HEIGHT = 180


# ============================================================
# HELPERS
# ============================================================

def save_rgb_image(image, path):
    """
    Save an RGB image returned by Isaac Sim.
    """
    image = np.asarray(image)

    # Some camera APIs can return RGBA.
    if image.shape[-1] == 4:
        image = image[..., :3]

    image = image.astype(np.uint8)

    Image.fromarray(image, mode="RGB").save(path)


# ============================================================
# CREATE OUTPUT DIRECTORIES
# ============================================================

(OUTPUT_DIR / "images" / "exterior").mkdir(
    parents=True,
    exist_ok=True,
)

(OUTPUT_DIR / "images" / "wrist").mkdir(
    parents=True,
    exist_ok=True,
)

(OUTPUT_DIR / "state").mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# LOAD USD
# ============================================================

omni.usd.get_context().open_stage(USD_PATH)

stage = omni.usd.get_context().get_stage()

print("\nLoaded stage:")
print(stage.GetRootLayer().realPath)


# ============================================================
# CREATE SIMULATION WORLD
# ============================================================

world = World(
    stage_units_in_meters=1.0,
)

world.reset()


# ============================================================
# CREATE ROBOT HANDLE
# ============================================================

robot = Articulation(
    prim_path=ROBOT_PRIM,
    name="franka",
)

robot.initialize()


# ============================================================
# CREATE CAMERA HANDLES
# ============================================================

exterior_camera = Camera(
    prim_path=EXTERIOR_CAMERA_PRIM,
    frequency=30,
    resolution=(WIDTH, HEIGHT),
)

wrist_camera = Camera(
    prim_path=WRIST_CAMERA_PRIM,
    frequency=30,
    resolution=(WIDTH, HEIGHT),
)

exterior_camera.initialize()
wrist_camera.initialize()


# ============================================================
# METADATA
# ============================================================

metadata = {
    "usd_path": USD_PATH,
    "robot_prim": ROBOT_PRIM,
    "exterior_camera_prim": EXTERIOR_CAMERA_PRIM,
    "wrist_camera_prim": WRIST_CAMERA_PRIM,
    "width": WIDTH,
    "height": HEIGHT,
    "num_frames": NUM_FRAMES,
}

with open(OUTPUT_DIR / "metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)


# ============================================================
# START SIMULATION
# ============================================================

world.play()

print("\n" + "=" * 80)
print("RECORDING")
print("=" * 80)


# ============================================================
# RECORD LOOP
# ============================================================

for frame_idx in range(NUM_FRAMES):

    # Advance simulation.
    world.step(render=True)

    # --------------------------------------------------------
    # Robot state
    # --------------------------------------------------------

    joint_positions = robot.get_joint_positions()
    joint_velocities = robot.get_joint_velocities()

    # Root/world pose of the articulation.
    # This is useful for debugging but is NOT the DROID EEF state.
    root_position, root_orientation = robot.get_world_pose()

    # --------------------------------------------------------
    # Camera images
    # --------------------------------------------------------

    exterior_rgba = exterior_camera.get_rgba()
    wrist_rgba = wrist_camera.get_rgba()

    # --------------------------------------------------------
    # Save images
    # --------------------------------------------------------

    save_rgb_image(
        exterior_rgba,
        OUTPUT_DIR
        / "images"
        / "exterior"
        / f"{frame_idx:06d}.png",
    )

    save_rgb_image(
        wrist_rgba,
        OUTPUT_DIR
        / "images"
        / "wrist"
        / f"{frame_idx:06d}.png",
    )

    # --------------------------------------------------------
    # Save robot state
    # --------------------------------------------------------

    np.savez(
        OUTPUT_DIR
        / "state"
        / f"{frame_idx:06d}.npz",

        joint_positions=np.asarray(
            joint_positions,
            dtype=np.float32,
        ),

        joint_velocities=np.asarray(
            joint_velocities,
            dtype=np.float32,
        ),

        root_position=np.asarray(
            root_position,
            dtype=np.float32,
        ),

        root_orientation=np.asarray(
            root_orientation,
            dtype=np.float32,
        ),
    )

    # --------------------------------------------------------
    # Print first frame
    # --------------------------------------------------------

    if frame_idx == 0:

        print("\nRobot state")
        print("--------------------")

        print(
            "joint_positions:",
            np.asarray(joint_positions).shape,
        )

        print(joint_positions)

        print(
            "joint_velocities:",
            np.asarray(joint_velocities).shape,
        )

        print(
            "root_position:",
            root_position,
        )

        print(
            "root_orientation:",
            root_orientation,
        )

        print("\nCamera")
        print("--------------------")

        print(
            "external:",
            np.asarray(exterior_rgba).shape,
        )

        print(
            "wrist:",
            np.asarray(wrist_rgba).shape,
        )

print("\nRecording finished.")

simulation_app.close()
```

---

# 3.3 Change these three paths

At the top:

```python
USD_PATH = ...
ROBOT_PRIM = ...
EXTERIOR_CAMERA_PRIM = ...
WRIST_CAMERA_PRIM = ...
```

Use the paths you discovered from `inspect_scene.py`.

For example:

```python
USD_PATH = "/home/steven/groot-poc/droid_scene/franka_droid_scene.usd"

ROBOT_PRIM = "/World/Franka"

EXTERIOR_CAMERA_PRIM = "/World/exterior_camera"

WRIST_CAMERA_PRIM = "/World/Franka/panda_hand/wrist_camera"
```

**Do not assume these are your actual paths.**

---

# 3.4 Run the recorder

```bash
~/isaacsim/python.sh \
    ~/groot-poc/isaac_droid_sim/record_droid.py
```

Isaac Sim should open.

It will simulate 100 frames.

Then check:

```bash
find ~/groot-poc/data/droid_sim/episode_000 -type f | head -30
```

You should see:

```text
metadata.json

images/exterior/000000.png
images/exterior/000001.png
...

images/wrist/000000.png
images/wrist/000001.png
...

state/000000.npz
state/000001.npz
...
```

---

# 4. Inspect what we actually recorded

Before touching GR00T, let's inspect one frame.

Create:

```bash
nano ~/groot-poc/isaac_droid_sim/inspect_recording.py
```

```python
from pathlib import Path

import numpy as np
from PIL import Image


DATASET = Path(
    "/home/YOUR_USERNAME/groot-poc/data/droid_sim/episode_000"
)


frame = 0


# ------------------------------------------------------------
# Images
# ------------------------------------------------------------

external = np.asarray(
    Image.open(
        DATASET
        / "images"
        / "exterior"
        / f"{frame:06d}.png"
    )
)

wrist = np.asarray(
    Image.open(
        DATASET
        / "images"
        / "wrist"
        / f"{frame:06d}.png"
    )
)


# ------------------------------------------------------------
# State
# ------------------------------------------------------------

state = np.load(
    DATASET
    / "state"
    / f"{frame:06d}.npz"
)


print("=" * 80)
print("RECORDED FRAME")
print("=" * 80)

print("\nExternal camera")
print("shape:", external.shape)
print("dtype:", external.dtype)

print("\nWrist camera")
print("shape:", wrist.shape)
print("dtype:", wrist.dtype)

print("\nRobot")

for key in state.files:
    value = state[key]

    print(
        f"{key:20s}",
        "shape =", value.shape,
        "dtype =", value.dtype,
    )

    print(value)

print("=" * 80)
```

Run:

```bash
python ~/groot-poc/isaac_droid_sim/inspect_recording.py
```

At this point we have completed **Point 2**:

> Record and save robot data + camera images locally.

---

# 5. Now prepare the data for GR00T

This is where we need to be precise.

GR00T's current Policy API expects:

```text
video
state
language
```

with:

```text
video:
    numpy uint8
    (B,T,H,W,3)

state:
    numpy float32
    (B,T,D)

language:
    list of lists of strings
```

and returns:

```text
action:
    numpy float32
    (B,T,D)
```

([GitHub][2])

For DROID specifically, the keys are:

```text
video:
    exterior_image_1_left
    wrist_image_left

state:
    eef_9d
    gripper_position
    joint_position

language:
    annotation.language.language_instruction
```

with state dimensions:

```text
eef_9d             9
gripper_position   1
joint_position     7
```

([GitHub][1])

---

# 6. Very important: our recorder does NOT yet have the correct DROID state

Our recorder currently has:

```text
joint_positions
joint_velocities
root_position
root_orientation
```

That is intentional.

We first record the **raw simulator information**.

We then transform it.

For example:

```text
Isaac Sim

joint positions
EEF pose
gripper
        ↓
DROID transformation
        ↓
eef_9d
gripper_position
joint_position
```

This separation is good engineering.

---

# 7. The DROID `eef_9d`

DROID uses:

```text
eef_9d
```

which is:

```text
3 position values
+
6D rotation representation
```

so:

```text
[x, y, z,
 r1, r2, r3,
 r4, r5, r6]
```

NVIDIA explicitly describes it as relative end-effector XYZ + rotation 6D. ([GitHub][1])

The conversion from your Franka pose needs to be done carefully.

**Do not just feed the quaternion into those nine values.**

---

# 8. First make a GR00T-format dataset

Create:

```bash
nano ~/groot-poc/isaac_droid_sim/prepare_groot.py
```

For the first version, I recommend preparing the camera portion and joint state first, while explicitly keeping the EEF conversion as a separate function.

```python
from pathlib import Path

import numpy as np
from PIL import Image


# ============================================================
# SETTINGS
# ============================================================

INPUT = Path(
    "/home/YOUR_USERNAME/groot-poc/data/droid_sim/episode_000"
)

OUTPUT = Path(
    "/home/YOUR_USERNAME/groot-poc/data/droid_sim/episode_000_groot"
)

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# CAMERA SETTINGS
# ============================================================

CAMERA_WIDTH = 320
CAMERA_HEIGHT = 180


# ============================================================
# LOAD IMAGE
# ============================================================

def load_rgb(path):

    image = np.asarray(
        Image.open(path).convert("RGB"),
        dtype=np.uint8,
    )

    return image


# ============================================================
# PLACEHOLDER EEF CONVERSION
# ============================================================

def convert_eef_to_droid(state):

    """
    Convert Isaac Sim EEF pose into DROID eef_9d.

    IMPORTANT:
    This function is intentionally not guessing the exact
    coordinate-frame conversion yet.

    We will implement this after confirming the exact Franka
    end-effector prim and coordinate convention in your scene.
    """

    raise NotImplementedError(
        "EEF → DROID conversion must be implemented "
        "after verifying the Franka EEF pose."
    )


# ============================================================
# PROCESS ONE FRAME
# ============================================================

frame = 0

external = load_rgb(
    INPUT
    / "images"
    / "exterior"
    / f"{frame:06d}.png"
)

wrist = load_rgb(
    INPUT
    / "images"
    / "wrist"
    / f"{frame:06d}.png"
)

state = np.load(
    INPUT
    / "state"
    / f"{frame:06d}.npz"
)

joint_position = np.asarray(
    state["joint_positions"],
    dtype=np.float32,
)


print("External:")
print(
    external.shape,
    external.dtype,
)

print("Wrist:")
print(
    wrist.shape,
    wrist.dtype,
)

print("Joint:")
print(
    joint_position.shape,
    joint_position.dtype,
)


# ============================================================
# CHECK DROID JOINT DIMENSION
# ============================================================

if joint_position.shape[-1] != 7:

    raise RuntimeError(
        "Expected 7 Franka arm joint positions, "
        f"got {joint_position.shape}"
    )


print("\nCamera data is ready for GR00T.")

print("\nNext required transformation:")
print("  Isaac EEF pose")
print("       ↓")
print("  DROID eef_9d")


# Do not continue until EEF conversion is implemented.
convert_eef_to_droid(state)
```

Run:

```bash
python ~/groot-poc/isaac_droid_sim/prepare_groot.py
```

It should intentionally stop with:

```text
NotImplementedError
```

That is **not a failure**.

It tells us:

> We have reached the one piece that must be defined correctly before allowing GR00T to control anything.

---

# 9. Why I'm deliberately stopping here

There is a dangerous shortcut:

```text
Franka joint positions
        ↓
pretend they are DROID joint positions
        ↓
GR00T
        ↓
send action
```

I don't want you doing that.

The GR00T documentation says the embodiment tag determines the modality configuration, state/action keys, and normalization, and the tag must match the robot type/data. ([GitHub][2])

Your simulation is:

```text
Franka Panda
```

while we're currently selecting:

```text
OXE_DROID_RELATIVE_EEF_RELATIVE_JOINT
```

So we need to define exactly how our simulated Franka maps into that DROID representation.

---

# 10. Nevertheless, we can already build the GR00T ingestion pipeline

Once the observation transformation is correct, the actual GR00T call is surprisingly simple.

Install/use your existing Isaac-GR00T environment.

From your GR00T checkout:

```bash
cd ~/Isaac-GR00T
```

or wherever your repository is.

Create:

```text
~/groot-poc/isaac_droid_sim/run_groot.py
```

Use:

```python
import numpy as np

from gr00t.policy import Gr00tPolicy


MODEL = "nvidia/GR00T-N1.7-3B"

EMBODIMENT = (
    "OXE_DROID_RELATIVE_EEF_RELATIVE_JOINT"
)


policy = Gr00tPolicy(
    model_path=MODEL,
    embodiment_tag=EMBODIMENT,
    device="cuda:0",
    strict=True,
)


# ------------------------------------------------------------
# EXAMPLE PLACEHOLDER
#
# These must come from prepare_groot.py.
# ------------------------------------------------------------

external_image = np.zeros(
    (1, 2, 180, 320, 3),
    dtype=np.uint8,
)

wrist_image = np.zeros(
    (1, 2, 180, 320, 3),
    dtype=np.uint8,
)

eef_9d = np.zeros(
    (1, 1, 9),
    dtype=np.float32,
)

gripper_position = np.zeros(
    (1, 1, 1),
    dtype=np.float32,
)

joint_position = np.zeros(
    (1, 1, 7),
    dtype=np.float32,
)


observation = {

    "video": {

        "exterior_image_1_left":
            external_image,

        "wrist_image_left":
            wrist_image,
    },

    "state": {

        "eef_9d":
            eef_9d,

        "gripper_position":
            gripper_position,

        "joint_position":
            joint_position,
    },

    "language": {

        "annotation.language.language_instruction":
            [["move toward the cube"]],
    },
}


# ------------------------------------------------------------
# RUN GR00T
# ------------------------------------------------------------

action, info = policy.get_action(
    observation
)


print("\n")
print("=" * 80)
print("GR00T OUTPUT")
print("=" * 80)

for key, value in action.items():

    print(
        f"\n{key}"
    )

    print(
        "shape:",
        value.shape,
    )

    print(
        "dtype:",
        value.dtype,
    )

    print(value)

print("\n")
```

This follows the current GR00T Policy API: nested `video/state/language` observation, then `policy.get_action()`, which returns nested action arrays. ([GitHub][2])

---

# 11. Notice the important temporal dimension

I deliberately used:

```python
(1, 2, 180, 320, 3)
```

for the cameras.

Why?

Because GR00T does not simply expect:

```text
H × W × 3
```

It expects:

```text
B × T × H × W × 3
```

where:

```text
B = batch
T = temporal observations
```

The exact `T` should come from the model's modality configuration. NVIDIA explicitly recommends querying the modality configuration rather than assuming the temporal horizon. ([GitHub][2])

So after we get your real data working, we will replace the hard-coded `2` with the actual DROID configuration.

---

# 12. Do not use zero images in the real run

The code above is only a skeleton showing the interface.

Your actual pipeline will eventually be:

```text
episode_000
    ↓
prepare_groot.py
    ↓
observation
    ↓
run_groot.py
    ↓
action
```

For example:

```python
observation = {
    "video": {
        "exterior_image_1_left": exterior_video,
        "wrist_image_left": wrist_video,
    },

    "state": {
        "eef_9d": eef_history,
        "gripper_position": gripper_history,
        "joint_position": joint_history,
    },

    "language": {
        "annotation.language.language_instruction":
            [["move toward the cube"]],
    },
}
```

---

# 13. Run GR00T

Once the observation is real:

```bash
cd ~/Isaac-GR00T

uv run python \
    ~/groot-poc/isaac_droid_sim/run_groot.py
```

The model will load and produce something like:

```text
GR00T OUTPUT

eef_9d
shape: (1, 40, 9)

gripper_position
shape: (1, 40, 1)

joint_position
shape: (1, 40, 7)
```

The exact horizon comes from the current DROID modality configuration. The important point is that GR00T can return an **action chunk**, not merely one action. The Policy API documents the `(B,T,D)` structure and taking `action[:,0,:]` for the first action. ([GitHub][2])

---

# 14. Point 5 — convert GR00T output back to Isaac Sim

This is the final bridge:

```text
GR00T

eef_9d
gripper
joint
   ↓
Isaac Sim command
```

There are two very different possibilities.

## Option A — Joint-space action

If the action is:

```text
7 joint positions
```

then it is comparatively simple:

```python
robot.set_joint_positions(
    joint_target
)
```

## Option B — EEF action

DROID's primary EEF action is:

```text
XYZ
+
rotation 6D
```

That means:

```text
GR00T
 ↓
desired EEF pose
 ↓
inverse kinematics
 ↓
7 joint positions
 ↓
Franka
```

This is why your previous Isaac Lab `run_diff_ik.py` experience is useful.

Isaac Lab's differential IK controller exists specifically to turn end-effector commands into joint commands.

---

# 15. For the first robot-control test, use only one action

Suppose GR00T gives:

```python
action["eef_9d"]
```

with:

```text
(B,T,9)
```

Don't execute all 40 actions.

Take:

```python
first_action = action["eef_9d"][:, 0, :]
```

The Policy API explicitly documents this pattern for taking the first predicted action. ([GitHub][2])

Conceptually:

```text
GR00T
 │
 │ 40 predicted future actions
 ↓
[0] [1] [2] [3] ... [39]
 │
 ↓
execute [0]
```

Then:

```text
simulate
 ↓
capture new observation
 ↓
GR00T
 ↓
execute new action
```

---

# 16. The final control loop

Eventually your Python program becomes approximately:

```python
while simulation_is_running:

    # --------------------------------------------------------
    # 1. Capture Isaac Sim observation
    # --------------------------------------------------------

    observation = capture_observation()


    # --------------------------------------------------------
    # 2. Convert to GR00T format
    # --------------------------------------------------------

    groot_observation = (
        convert_to_groot(observation)
    )


    # --------------------------------------------------------
    # 3. GR00T inference
    # --------------------------------------------------------

    action, info = policy.get_action(
        groot_observation
    )


    # --------------------------------------------------------
    # 4. Select first action
    # --------------------------------------------------------

    first_action = extract_first_action(
        action
    )


    # --------------------------------------------------------
    # 5. Convert GR00T action to Isaac command
    # --------------------------------------------------------

    robot_command = (
        convert_groot_action_to_isaac(
            first_action
        )
    )


    # --------------------------------------------------------
    # 6. Move Franka
    # --------------------------------------------------------

    apply_robot_command(
        robot_command
    )


    # --------------------------------------------------------
    # 7. Advance simulation
    # --------------------------------------------------------

    simulation.step()
```

That's your desired:

```text
Isaac Sim
    ↓
camera + robot state
    ↓
GR00T observation
    ↓
GR00T
    ↓
GR00T action
    ↓
Isaac Sim command
    ↓
Franka
    ↓
new observation
    ↓
...
```

---

# 17. Later, turn this into an Isaac Lab environment

Only **after** the above works should we move to:

```text
Isaac Lab
    ↓
observation
    ↓
GR00T
    ↓
action
    ↓
Isaac Lab controller
```

At that point, the code becomes cleaner because Isaac Lab already gives you structured robot state, controllers and sensors.

And NVIDIA's GR00T documentation explicitly describes this type of environment adapter: transform environment observations → Policy API observations → `get_action()` → transform policy actions back into environment actions. ([GitHub][2])

---

# 18. Later still: use the GR00T server

You don't need this yet.

Once your same-process version works, you can separate GR00T:

```text
Terminal 1

Isaac Sim
    ↓
PolicyClient
    ↓
network
```

and:

```text
Terminal 2

GR00T server
    ↓
GPU
    ↓
GR00T
```

NVIDIA officially supports this architecture with `run_gr00t_server.py` and `PolicyClient`. ([GitHub][2])

For example:

```bash
cd ~/Isaac-GR00T

uv run python gr00t/eval/run_gr00t_server.py \
    --model-path nvidia/GR00T-N1.7-3B \
    --embodiment-tag OXE_DROID_RELATIVE_EEF_RELATIVE_JOINT \
    --device cuda:0
```

Then the simulator becomes the client.

But **do not introduce ZMQ yet**.

---

# 19. What I want you to do now

Don't implement all five stages at once.

Do exactly this first:

### Stage A — UI

Build:

```text
Franka
+
gripper
+
ground
+
cube
+
external_camera
+
wrist_camera
```

Save:

```text
~/groot-poc/droid_scene/franka_droid_scene.usd
```

### Stage B — Python

Run:

```bash
~/isaacsim/python.sh \
    ~/groot-poc/isaac_droid_sim/inspect_scene.py
```

and identify:

```text
Franka prim
external camera prim
wrist camera prim
Franka hand/wrist prim
```

### Stage C — Recording

Run:

```bash
~/isaacsim/python.sh \
    ~/groot-poc/isaac_droid_sim/record_droid.py
```

and confirm you have:

```text
data/droid_sim/episode_000/
├── images/
│   ├── exterior/
│   └── wrist/
└── state/
```

### Stage D — Inspect

Run:

```bash
python \
    ~/groot-poc/isaac_droid_sim/inspect_recording.py
```

---

## And then stop.

**Do not implement the GR00T transformation yet.**

At that point, send me:

1. the output of `inspect_scene.py`, especially the Franka/camera prim paths;
2. the output of `inspect_recording.py`;
3. if the recorder errors, the complete error.

Then I can give you the **next exact script** that converts *your actual Franka state* into the DROID `eef_9d + gripper_position + joint_position` representation, rather than guessing your USD hierarchy or coordinate conventions.

That is the safest way to get from:

```text
UI-created Franka
        ↓
real recorded simulation data
        ↓
DROID-format observation
        ↓
GR00T
        ↓
real simulated Franka movement
```

without you having to learn Isaac Sim's entire Python API at once.

[1]: https://github.com/NVIDIA/Isaac-GR00T/blob/main/examples/DROID/README.md?utm_source=chatgpt.com "Isaac-GR00T/examples/DROID/README.md at main · NVIDIA/Isaac-GR00T · GitHub"
[2]: https://github.com/NVIDIA/Isaac-GR00T/blob/main/getting_started/policy.md?utm_source=chatgpt.com "Isaac-GR00T/getting_started/policy.md at main · NVIDIA/Isaac-GR00T · GitHub"

