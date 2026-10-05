# algorithm-gesture-game-project
ខ្លាស៊ីគោ (Khla Si Ko) — Tiger Eats Cow

Project Overview

Khla Si Ko (ខ្លាស៊ីគោ / Tiger Eats Cow) is a two-player traditional Khmer-style hand game implemented as a computer-vision application.

The game uses a webcam to detect each player's hand gesture and converts the gesture into an in-game choice. Players interact with the game without touching the screen and without using a keyboard or physical game controller.

This project demonstrates practical applications of:

Python

Computer vision

Hand tracking

Gesture recognition

Real-time interaction

Game logic

UI design

Software architecture

Project Goals

The project aims to:

Build a playable two-player version of ខ្លាស៊ីគោ using a standard webcam.

Recognize player hand gestures in real time.

Allow both players to play without touching the display.

Convert recognized gestures into game actions reliably.

Display game state, choices, countdown, result, and score clearly.

Provide sound and visual feedback.

Keep the project structure clean and understandable.

Game Concept

The game follows a rock-paper-scissors-style relationship represented by the local version of ខ្លាស៊ីគោ.

The exact gesture-to-character mapping must be configured according to the teacher's/local game rules.

Possible choices include:

Choice

Gesture

Display

ខ្លា (Tiger)

Configured hand pose

Tiger icon/image

គោ (Cow)

Configured hand pose

Cow icon/image

Third choice / optional

Configured hand pose

Game icon/image

Important: Before implementing the final game rules, confirm the exact local/traditional rules, including the number of choices, hand shapes, and which choice defeats which.

Features

Main Game

Two-player gameplay

One webcam for both players

Separate Player 1 and Player 2 play areas

Real-time hand detection

Gesture recognition

Countdown before each round

WIN / LOSE / DRAW result

Individual player scores

Configurable winning score

Next round and restart flow

Gesture Recognition

The system should:

Detect hand landmarks.

Normalize landmark coordinates where appropriate.

Support left/right hand orientation where required.

Use a confidence threshold.

Ignore ambiguous or low-confidence gestures.

Require gesture stability before accepting a choice.

Prevent repeated detections from creating multiple selections.

Keep gestures inside the player's defined region.

User Interface

The interface should display:

Game title

Player names/labels

Camera view or masked camera view

Countdown

Recognized choices

Round result

Score

Restart

Next Round

Exit

The UI should use Khmer and/or English labels consistently and should be suitable for a large display or classroom demonstration.

Audio and Visual Feedback

Optional feedback includes:

Countdown sound

Gesture confirmation sound

Win sound

Lose sound

Draw sound

Simple result animations

Audio should be able to be enabled or disabled.

Technology Stack

Technology

Purpose

Python 3.11+

Main development language

OpenCV

Webcam capture and image processing

MediaPipe Hands

Hand landmark detection and tracking

Pygame

Game window, UI, sprites, animation, and keyboard fallback

NumPy

Image and landmark calculations

Pygame Mixer

Sound effects and background audio

Project Architecture

The project is organized into the following layers:

Camera Layer
      ↓
Preprocessing Layer
      ↓
Hand Detection Layer
      ↓
Gesture Recognition Layer
      ↓
Game Rules Engine
      ↓
Game State Manager
      ↓
UI / Rendering Layer
      ↓
Audio Layer
      ↓
Configuration Layer

Layer Responsibilities

Camera Layer

Captures frames from the webcam.

Preprocessing Layer

Resizes frames.

Flips frames when required.

Converts image colors.

Optionally extracts player regions.

Hand Detection Layer

Detects hand landmarks for each player.

Gesture Recognition Layer

Converts hand landmarks into a game gesture.

Game Rules Engine

Determines WIN, LOSE, DRAW, or INVALID.

Game State Manager

Manages menu, setup, countdown, detection, result, score, and game-over states.

UI / Rendering Layer

Displays camera, players, icons, text, animations, and results.

Audio Layer

Plays countdown and result sounds.

Configuration Layer

Stores gesture mappings, confidence threshold, FPS, sound settings, and winning score.

Project Structure

khla-si-ko/
│
├── main.py
├── requirements.txt
├── README.md
│
├── src/
│   ├── camera.py
│   ├── hand_tracker.py
│   ├── gesture_recognizer.py
│   ├── game_rules.py
│   ├── game_state.py
│   ├── renderer.py
│   ├── audio_manager.py
│   └── config.py
│
├── assets/
│   ├── images/
│   ├── icons/
│   ├── sounds/
│   └── fonts/
│
├── tests/
│   ├── test_gesture.py
│   └── test_game_rules.py
│
└── docs/
    └── project-requirements.docx

Installation

1. Check Python

The project requires Python 3.11 or newer.

python --version

2. Create a Virtual Environment

Windows:

python -m venv .venv

Activate it in PowerShell:

.venv\Scripts\Activate.ps1

3. Install Dependencies

pip install -r requirements.txt

Running the Project

After the environment and dependencies are installed:

python main.py

The application should provide:

Main Menu
   ↓
Start Game
   ↓
Player Setup
   ↓
Camera Ready
   ↓
Countdown
   ↓
Gesture Detection
   ↓
Result
   ↓
Score Update
   ↓
Next Round / Game Over

Game State Flow

MENU
  │
  └── Start Game
        ↓
      SETUP
        ↓
    COUNTDOWN
        ↓
      DETECT
        ↓
      RESULT
        ↓
  SCORE_UPDATE
     │       │
     │       └── Target score reached → GAME_OVER
     │
     └── Target score not reached → COUNTDOWN

Gesture Recognition Pipeline

The intended recognition pipeline is:

1. Capture camera frame
        ↓
2. Detect Player 1 and Player 2 hand landmarks
        ↓
3. Extract normalized landmark features
        ↓
4. Classify each hand pose
        ↓
5. Apply confidence threshold
        ↓
6. Apply stability / smoothing rule
        ↓
7. Return one game choice per player

Performance Targets

The requirements specify the following targets:

Category

Target

Real-time processing

20–30 FPS on a typical training-room laptop

Gesture latency

Preferably below 300 ms after stable detection

Gesture accuracy

Target ≥90% in controlled lighting after calibration

Learning curve

Player understands controls in under 2 minutes

Reliability

No crash during a normal 10-minute play session

Operating system

Windows first; Linux/macOS where dependencies permit

Testing

The project should test:

Camera opening and safe release

One-hand detection

Two-hand detection

Gesture recognition

Gesture stability

Simultaneous two-player detection

Game rules

Score updates

UI visibility

Audio feedback

Camera/hand detection recovery

Continuous performance

Example:

python -m pytest

Error Handling

The application should handle:

Camera unavailable

Camera frame problems

Missing or unsupported model files

One player's hand not being detected

Temporary hand detection loss

Invalid or low-confidence gestures

The game should not unexpectedly terminate because of temporary camera or detection problems.

Privacy

Camera frames should be processed locally by default.

The project should:

Not upload camera images or biometric/hand data to an external server unless explicitly required.

Not store player images by default.

Provide a user-controlled option if screenshots or recordings are added later.

Development Phases

Phase 1  → Game design
Phase 2  → Camera prototype
Phase 3  → Hand tracking
Phase 4  → Gesture recognition
Phase 5  → Rules engine
Phase 6  → Game UI
Phase 7  → Integration
Phase 8  → Polish
Phase 9  → Testing
Phase 10 → Deployment

Recommended Development Order

For implementation, build the project incrementally:

Confirm the game rules.

Open and display the webcam.

Detect and display hand landmarks.

Detect both players.

Recognize the supported gestures.

Implement and test the game rules.

Add countdown and game states.

Add score management.

Build the complete UI.

Add sounds and animations.

Test different lighting, distances, users, and computers.

Prepare the final demonstration.

Acceptance Criteria

The project is considered successful when:

The application launches successfully.

Two players can play using one webcam.

Supported gestures are detected and mapped correctly.

Players do not need to touch the screen.

The round result follows the confirmed game rules.

Scores update correctly.

Countdown, result, and invalid/missing detection feedback are clear.

The application runs continuously during a normal demonstration.

Installation and execution instructions are documented.

Risks and Mitigation

Risk

Mitigation

Poor lighting

Use adequate lighting, preprocessing, and user guidance

Players overlap

Use player regions/ROIs and correct camera positioning

Gesture ambiguity

Use stable-frame validation and clear gesture definitions

Low camera resolution

Use a suitable webcam and configurable resolution

Background clutter

Use a simple background where possible

Different hand sizes

Normalize landmarks and test with multiple users

Low FPS

Resize frames, limit processing resolution, and optimize the pipeline

Future Enhancements

Possible future features include:

Single-player mode against an AI

Tournament mode

Multiple cameras

Custom gesture training/calibration

Leaderboard and match statistics

Khmer voice announcements

Online multiplayer

Automatic game recording

Gesture confidence and reaction-time analytics

Project Deliverables

The completed project should include:

Complete Python source code

requirements.txt

Game assets with usage rights documented

README.md

Project requirements document

System architecture diagram

Game flow/state diagram

Gesture mapping documentation

Unit and functional test results

Short demonstration video or live demonstration

License

This project is an educational computer-vision game project.

