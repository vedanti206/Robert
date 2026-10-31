@echo off
title Installing Robert's parts
echo.
echo  Installing Robert's parts. Please wait, this can take a few minutes...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo  ===============================================
echo   If you see no red errors above, it worked!
echo   Next: follow Step 4 in the guide.
echo  ===============================================
pause
