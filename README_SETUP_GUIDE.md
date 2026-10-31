# Robert the Desktop Puppy - Setup Guide (easy version)







Follow the steps in order. Do not skip. Each step is small.

---

## Step 1 - Install Python (Robert's engine)
1. Open your browser and go to: **python.org/downloads**
2. Click the big yellow **Download Python** button. (Python 3.11 or 3.12 is best.)
3. Open the file you downloaded.
4. **VERY IMPORTANT:** at the bottom, tick the box **"Add python.exe to PATH"**.
5. Click **Install Now**. Wait. Click **Close**.

Check it worked: press the Windows key, type `cmd`, press Enter. In the black window type
`python --version` and press Enter. You should see something like `Python 3.12.x`.

## Step 2 - Put Robert's folder in a good place
1. Unzip `Robert.zip`.
2. Move the folder `Robert` to your **C: drive** or **Documents**. Example: `C:\Robert`
3. Put Robert's picture sheet inside the folder named `assets`.
   - The file must be named exactly: `robert_sheet.png`
   - It must be the CLEAN picture: no row names, no green boxes, and a see-through background.
   - The sheet must be 640 x 801 pixels: 8 pictures across and 9 rows.
   - To use the individual sticker pack instead, copy its PNG files into a folder named `sprites` inside Robert's folder. These pictures replace Robert's idle, greeting, listening, working, thinking, and sleeping animations. The sheet remains useful for other animations.
   - If neither the sheet nor individual sprites are available, Robert still starts as a simple drawn puppy.
   - Check it in the Robert folder with `python check_sheet.py`. It should report `640 x 801` and `80 x 89`.

## Step 3 - Install Robert's parts
1. Open the Robert folder.
2. Double-click **install_robert.bat**.
3. A black window opens and downloads things. Wait until it says "Press any key". This can take 3 to 10 minutes.
4. Press any key to close it.

## Step 4 - Give Robert his hearing model (so he knows his name)
1. Go to: **alphacephei.com/vosk/models**
2. Find **vosk-model-small-en-us-0.15** (about 40 MB). Click it to download.
3. Right-click the downloaded zip and choose **Extract All**.
4. Inside you will see a folder called `vosk-model-small-en-us-0.15`.
5. In the Robert folder, make a new folder named **model**.
6. Put the contents inside `model`, so that this path exists:
   `Robert\model\am`   (it also works if it is `Robert\model\vosk-model-small-en-us-0.15\am`)

## Step 5 - Give Robert a brain (Ollama)
1. Go to: **ollama.com/download** and download the Windows installer.
2. Open it and click Install. Ollama will sit near your clock (bottom right).
3. Open **cmd** (Windows key, type `cmd`, Enter).
4. Type this and press Enter:
   `ollama pull llama3.2:3b`
5. Wait for the download (about 2 GB). When it says **success**, you are done.
6. Test it: type `ollama run llama3.2:3b`, say "hi", then type `/bye`.

## Step 6 - Add your WhatsApp friends
1. Right-click **contacts.json** -> Open with -> Notepad.
2. Change the names and numbers. Use the country code, like `+91`.
3. Keep the quotes and commas. No comma after the last friend. Save.

## Step 7 - Start Robert!
1. Make sure Ollama is running (small icon near the clock).
2. Double-click **start_robert.bat**.
3. Robert appears at the bottom-right of your screen and waves.

## Step 8 - Talk to Robert
- Click Robert to open the command box above his head. Type a task and press Enter, or click the microphone button to talk.
- Click Robert again, click **X**, or press **Esc** to close the command box. His answer appears in a bubble above it.
- Right-click Robert for the menu, including **Quit Robert**.
- Drag him with the mouse to move him.
- You can also say **"Robert"**, wait for the beep, then say what you want.

### Things to say
| Say this | What happens |
|---|---|
| play arijit singh songs on youtube | Opens the video |
| open chrome / open notepad / open github | Opens it |
| message rahul I will be late | Asks "yes or no?" then sends on WhatsApp |
| set a timer for 10 minutes | Timer |
| remind me in 30 minutes to drink water | Reminder |
| start pomodoro / pomodoro status / stop pomodoro | Study timer: 25 min work, 5 min break |
| what is the weather / weather in Nagpur | Weather |
| what time is it / what is the date | Time and date |
| take a note buy milk / read my notes | Notes (saved in notes.txt) |
| volume up / volume down / mute / set volume to 40 | Sound |
| brightness up / set brightness to 60 | Screen light |
| take a screenshot | Saved in Pictures\Robert Screenshots |
| lock the screen / battery status | Lock and battery |
| read my clipboard / summarize this / translate this to Hindi | Copy some text first |
| study mode on | Explains everything in simple steps |
| explain TCP/IP (or any question) | Robert's brain answers |
| blush | Shows Robert's blushing picture |
| give us a compliment | Shows and says a random compliment |
| Robert, you are smart | Shows Robert reading with glasses |
| play / play games for some time | Loops the chess pictures for 30 seconds; say "Robert" to stop sooner |
| read / read a book | Loops the reading pictures until you say "Robert" |
| Robert, say hi | Shows the "Hiiii!!" greeting picture and says hello |
| next song / pause / play music | Media keys |
| skip the ad / auto skip ads on / stop skipping ads | Skips a visible YouTube Skip button |
| be quiet / start talking | Voice off / on |
| go to sleep | Robert naps |

### YouTube ad skipping
1. On a YouTube ad, capture a small image of only the **Skip** button with **Windows + Shift + S**.
2. Paste it into Paint and save it as `assets\skip_button.png` in the Robert folder.
3. Say or type **"skip the ad"** to skip once, **"auto skip ads on"** to enable automatic skipping, or **"stop skipping ads"** to turn it off.

Automatic skipping only works while a YouTube window is active and the ad has a visible Skip button. If OpenCV is missing, install it with `python -m pip install opencv-python`.

---

## If something is wrong
- **"python is not recognized"**: Python was installed without the PATH box. Run the Python installer again, choose Modify/Repair, and tick "Add to PATH".
- **Robert does not hear his name**: Windows Settings -> Privacy & security -> Microphone -> turn ON "Let desktop apps access your microphone". Speak clearly, 30 cm from the laptop, in a quiet room. You can always click him instead.
- **Bubble says "I cannot find my voice model"**: Step 4 folder is wrong. Check that `Robert\model\am` exists.
- **"My brain is asleep"**: Open the Ollama app (Start menu), wait 10 seconds, ask again. First answer after starting is slow (10 to 30 seconds). This is normal on a laptop without a graphics card.
- **"I cannot find my brain file"**: Run `ollama pull llama3.2:3b` again.
- **Pictures look cut or mixed**: Open `config.py` and check `SHEET_COLUMNS` (8) and `SHEET_ROWS` (9).
- **WhatsApp opens but does not press send**: Open `config.py`, make `WHATSAPP_WAIT_SECONDS` bigger (like 12). Keep the WhatsApp app signed in.
- **He wakes up by himself too much**: Open `config.py` and set `WAKE_WORD` to a longer word, or just use click.
- **Robert is too big or small**: change `PET_SIZE` in `config.py`.
- **Want him fully offline?** In `config.py` set `USE_GOOGLE_SPEECH = False`.

Robert is made of these files: main.py (start), pet.py (body and bubble), voice.py (ears and mouth),
assistant.py (understands you), skills.py (does things), timers.py (timers), llm.py (brain), config.py (settings).
