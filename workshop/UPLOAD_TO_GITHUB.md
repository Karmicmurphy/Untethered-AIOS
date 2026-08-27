# Upload this build to GitHub

The repository currently appears empty and the connected ChatGPT GitHub tool has read-only access.

## Easiest GitHub web upload

1. Open:
   `https://github.com/Karmicmurphy/Ollie_Twis_Holo_workshop`
2. Click **uploading an existing file**.
3. Drag the contents of this unzipped folder into GitHub.
4. Commit to `main`.

## Git command line upload

```bash
git clone https://github.com/Karmicmurphy/Ollie_Twis_Holo_workshop.git
cd Ollie_Twis_Holo_workshop
# copy this package's files into the cloned repo folder
git add .
git commit -m "Add Twis Holo Workshop full build"
git push origin main
```

## Run locally

Double-click:

`start-workshop.bat`

Then open:

`http://127.0.0.1:8787`
