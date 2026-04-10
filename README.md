# Missing Lil Pudgys Scanner

![Lil Pudgys](https://i2c.seadn.io/collection/lilpudgys/overview/module/0/narrative/media/0/4fd8a2455b99470d075c590da2aaaa/fe4fd8a2455b99470d075c590da2aaaa.jpeg?w=1920)

This tool checks the list of unminted Lil Pudgys, downloads a preview image for each one, and shows you which corresponding Pudgy Penguins are currently available to buy on OpenSea.

Everything is saved to an `output/` folder when it's done.

---

## Before You Start

You need two things installed on your computer: **Python 3** and the tool's dependencies. Follow the steps for your operating system below.

---

## Step 1 — Install Python 3

### Mac

1. Open **Terminal** (press `Cmd + Space`, type `Terminal`, hit Enter)
2. Check if Python 3 is already installed by typing:
   ```
   python3 --version
   ```
   If you see something like `Python 3.11.x` you're good — skip to Step 2.
3. If not, go to **https://www.python.org/downloads/** and click the yellow **Download Python 3** button
4. Open the downloaded file and follow the installer
5. When it finishes, close and reopen Terminal, then run `python3 --version` to confirm

### Windows

1. Open **Command Prompt** (press `Win + R`, type `cmd`, hit Enter)
2. Check if Python 3 is already installed:
   ```
   python3 --version
   ```
   If you see something like `Python 3.11.x` you're good — skip to Step 2.
3. If not, go to **https://www.python.org/downloads/** and click the yellow **Download Python 3** button
4. Open the downloaded installer. **Important:** check the box that says **"Add Python to PATH"** before clicking Install
5. When it finishes, close and reopen Command Prompt, then run `python3 --version` to confirm

---

## Step 2 — Download This Tool

Download this repository as a ZIP file (green **Code** button → **Download ZIP**), then unzip it somewhere easy to find, like your Desktop.

Open Terminal (Mac) or Command Prompt (Windows) and navigate into the folder:

```
cd Desktop/missing-lil-pudgys
```

---

## Step 3 — Install Dependencies

Run this once to install the required libraries:

```
python3 -m pip install -r requirements.txt
```

---

## Step 4 — Get an OpenSea API Key

You need a free OpenSea API key to check which Pudgy Penguins are listed for sale.

1. Go to **https://docs.opensea.io/reference/api-keys**
2. Click **Get API Key** and sign up for a free account
3. Once you have your key, open the file called **`sample_data/opensea_key.txt`** in a text editor
4. Replace the placeholder text with your actual API key and save the file

> If you skip this step the tool will still run and download images, but it won't be able to check listing prices.

---

## Step 5 — Run It

```
python3 lilpudgys.run
```

That's it. The tool will:

1. Check which IDs from the list are still unminted
2. Download a preview image for each one
3. Generate a contact sheet showing all the missing tokens
4. Check which corresponding Pudgy Penguins are listed for sale on OpenSea
5. Save everything to the `output/` folder

---

## What You Get

After it runs, open the `output/` folder:

| File | What it is |
|---|---|
| `missing/` | Folder of downloaded preview images |
| `contact_sheet.png` | Printable grid of all missing token images |
| `buyable_only.csv` | Spreadsheet of tokens available to buy right now |
| `buyable_only.json` | Same data in JSON format |
| `report.csv` | Full results for every ID |
| `report.json` | Full results in JSON format |

---

## Troubleshooting

**"python3 is not recognized"** — Python was not added to your PATH during installation. Re-run the Python installer and make sure to check "Add Python to PATH".

**"No module named pip"** — Run `python3 -m ensurepip --upgrade` then try Step 3 again.

**Images download but no listing prices appear** — Your OpenSea API key is missing or incorrect. Double-check `sample_data/opensea_key.txt`.

**Some IDs were removed before downloading** — Those tokens were minted since the list was last updated. This is expected — the tool automatically filters them out.

---

## Advanced Options

If you're comfortable with the command line you can pass extra flags:

```
python3 lilpudgys.run --help
```

Useful flags:

| Flag | What it does |
|---|---|
| `--skip-mint-check` | Skip the "already minted?" check and use the list as-is |
| `--no-contact-sheet` | Don't generate the image grid |
| `--concurrency 10` | Run faster with more parallel connections |
| `--verbose` | Show detailed logs for every request |
