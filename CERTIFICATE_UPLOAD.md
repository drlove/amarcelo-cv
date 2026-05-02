# Certificate Upload Cheatsheet

## Every time you have new certificates

**1. Open Terminal and activate environment**
```bash
source ~/venvs/cv-env/bin/activate
```

**2. Go to the project folder**
```bash
cd /Users/amarcelo/githubprojects/amarcelo-cv
```

**3. Pull latest code**
```bash
git pull origin claude/certificate-processing-workflow-6Djke
```

**4. Copy your certificate files into the `in/` folder**
```bash
cp ~/Downloads/yourcertificate.pdf in/
```
Supported formats: `.pdf` `.jpg` `.jpeg` `.png`

**5. Run the script**
```bash
python3 process_certificates.py
```

**6. Push the updated CV to GitHub**
```bash
git add README.md done/
git commit -m "Add processed certificates"
git push origin claude/certificate-processing-workflow-6Djke
```

---

## Notes
- Processed certificates are moved to `done/` automatically with a timestamp in the filename
- The script prints `[OK] Verified` for each successful certificate
- Your API key must be set — if you see an authentication error run:
  ```bash
  export ANTHROPIC_API_KEY=sk-ant-api03--your-key-here
  ```
