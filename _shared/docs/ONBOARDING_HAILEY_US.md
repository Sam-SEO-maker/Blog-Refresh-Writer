# Content Writer — Your Onboarding Guide
### Superprof US · SEO Content Refresh System

> By the end of this guide, you will know how to install the system, configure your APIs, run a content refresh, and publish the result to WordPress — from scratch, with no prior technical experience.

**Last updated:** June 2026
**Questions?** Contact: `[your technical contact's name / Slack handle]`

---

## Table of Contents

1. [What This System Is and Your Role](#part-1--what-this-system-is-and-your-role)
2. [One-Time Setup](#part-2--one-time-setup)
   - Phase 1: Install VS Code, Python, and Claude Code
   - Phase 2: Get the Project Files (GitHub)
   - Phase 3: Python Environment
   - Phase 4: API Credentials (.env)
   - Phase 5: Google Service Account + Sheets + GSC
   - Phase 6: WordPress Application Password
   - Phase 7: Register Superprof US in the Project
   - Phase 8: Verify Everything Works
3. [Your Project Files — A Quick Tour](#part-3--your-project-files--a-quick-tour)
4. [Claude Code Modes](#part-4--claude-code-modes)
5. [The 7-Step Content Refresh Workflow](#part-5--the-7-step-content-refresh-workflow)
6. [Publishing to WordPress](#part-6--publishing-to-wordpress)
7. [Troubleshooting](#part-7--troubleshooting)
8. [Quick Reference Card](#part-8--quick-reference-card)

---

## PART 1 — What This System Is and Your Role

### The Problem It Solves

Superprof US has hundreds of blog articles. Many of them are losing Google traffic because they haven't been updated, their format doesn't match what Google currently rewards, or their keywords are drifting. Rewriting all of them manually would take months.

This system — **Content Writer** — automates the analysis and drafting work. It reads your Google Sheets tracking file, pulls live data from Google Search Console and DataForSEO, decides what each article needs, and uses Claude AI to write a refreshed version. You review the output and paste it into WordPress.

### The Three Things That Talk to Each Other

```
Google Sheets          →         Content Writer          →         WordPress
(your control panel)           (runs on your laptop)           (where it goes live)
```

- **Google Sheets** is where you track article URLs, see what action is recommended, and check status.
- **Content Writer** is the Python program that does the analysis and writes the HTML. It runs on your laptop inside VS Code.
- **WordPress** is where you paste the final output to publish the refreshed article.

> ℹ️ **Your daily workspace is just three places:** Google Sheets to check status, VS Code to run the system, and WordPress to publish. Everything else is infrastructure you set up once and then rarely touch.

### What Claude Does Here

Claude Code is an AI assistant that you talk to inside VS Code. Think of it as a capable writing assistant and co-pilot. You describe what you want to do, and it runs the right commands, reads the output, and helps you interpret results.

### What You Should Never Touch

Some parts of this project are the system's engine. Editing them without guidance can break things silently.

| File or Folder | Why Not to Touch It |
|---|---|
| `scripts/` | All automation code. Changes here require developer testing. |
| `CLAUDE.md` | The AI's rulebook — editorial guidelines, HTML rules. Only edit with approval from your technical contact. |
| `requirements.txt` | Python package list. Never edit manually. |
| `_shared/config/decision_rules.json` | Defines the logic the system uses to decide what refresh an article needs. |

---

### Adapting the System to Superprof US — What Claude Does vs. What You Provide

This system was originally built for two French blogs (Enseigna and Superprof FR). The editorial guidelines, prompts, and documentation files are in French. Before you run your first content refresh, the system needs to be localized for Superprof US.

**The good news:** Claude Code can handle most of this translation and adaptation in a single session. You do not need to edit files manually.

**What Claude Code can do for you (one session, one instruction):**

- Translate `CLAUDE.md` and all documentation in `_shared/docs/` into English
- Translate and adapt the generic editorial prompts in `_shared/prompts/`
- Create a new `superprof-us.md` prompt file for content generation, adapted from the French equivalent

To trigger this, open Claude Code in VS Code and type something like:

> *"Translate the system to English and adapt the prompts and guidelines for Superprof US. Keep the structure intact."*

Claude will go through the relevant files and adapt them. Review the output with your technical contact before running any content generation.

---

**What you must provide yourself — Claude cannot invent this:**

Claude can translate and adapt the system structure, but it cannot know the specific editorial identity of Superprof US. Before asking Claude to localize, gather the following and share it in the same conversation:

| What Claude Needs from You | Why It Matters |
|---|---|
| **Tone of voice** | Is the blog casual and encouraging, or more formal and informational? Any specific "dos and don'ts" for how articles should sound? |
| **Competitor blacklist** | Are there competitors you must never name or link to in your content? |
| **YMYL sensitivity** | Does Superprof US publish health, financial, or safety-sensitive content? If so, which topics? |
| **Formatting preferences** | Any specific HTML or structural conventions used in your WordPress theme? |
| **Subject categories covered** | What topics does the Superprof US blog cover? (e.g., math tutoring, language learning, music, etc.) |

The more specific you are, the better the adapted system will match your actual editorial standards.

---

**What is always your responsibility, regardless of localization:**

These are never generated by Claude — they are your credentials and your infrastructure:

- All API keys and passwords (`.env` file — see Phase 4)
- Google Service Account setup and sharing permissions (Phase 5)
- Your Google Sheets file ID and structure (Phase 5 and Phase 7)
- Your WordPress Application Password (Phase 6)

---

> ℹ️ **Recommended order:** Gather your editorial notes first → run the localization session with Claude Code → then proceed to Part 2 (technical setup). This ensures that by the time the system is installed and configured, the editorial guidelines already reflect Superprof US.

---

## PART 2 — One-Time Setup

This section covers everything you do **once** to get the system working. Work through the phases in order. Each phase ends with a clear checkpoint so you know when to move on.

---

### Phase 1 — Install VS Code, Python, and Claude Code

**Step 1: Install VS Code**

1. Go to [code.visualstudio.com](https://code.visualstudio.com)
2. Click the large download button for your operating system (macOS or Windows)
3. Open the downloaded file and follow the installer — accept all defaults

> 💡 **What is VS Code?** It is the main application you will open to use this system. Think of it as the cockpit. Everything runs from inside it.

**Step 2: Install Python 3.10 or higher**

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Python 3 installer for your OS
3. **Windows users:** During installation, check the box that says **"Add Python to PATH"** — this is important
4. Finish the installer with default settings

To verify it worked:
- **Mac:** Open Terminal (press `Cmd + Space`, type `Terminal`, press Enter)
- **Windows:** Open Command Prompt (press `Win + R`, type `cmd`, press Enter)
- Type: `python --version` and press Enter
- You should see something like: `Python 3.12.4`

> ⚠️ **If you see an error or Python 2.x:** The installation did not complete correctly. On Windows, re-run the installer and make sure "Add Python to PATH" is checked.

**Step 3: Install the Claude Code extension**

1. Open VS Code
2. Click the **Extensions** icon in the left sidebar (it looks like four squares)
3. In the search bar at the top, type: `Claude Code`
4. Install the extension published by **Anthropic**
5. When prompted, sign in with your Anthropic account

---

### Phase 2 — Get the Project Files (GitHub)

GitHub is where the project code is stored. You need to download a copy to your computer.

**Step 1: Create a GitHub account** (if you don't have one)

Go to [github.com](https://github.com) and sign up.

**Step 2: Get access to the repository**

Ask your technical contact to invite your GitHub account to the private Content Writer repository. You will receive an email invitation — accept it.

**Step 3: Clone the repository (download it)**

In Terminal (Mac) or Command Prompt (Windows), run:

```
git clone [THE_REPO_URL_PROVIDED_BY_YOUR_CONTACT]
```

This creates a folder called `Content Writer` on your computer (wherever your Terminal is currently pointed, usually your home folder or Desktop).

**Step 4: Open the project in VS Code**

1. Open VS Code
2. Go to **File → Open Folder**
3. Navigate to the `Content Writer` folder you just downloaded
4. Click **Open**

You should now see the project file tree in VS Code's left panel.

> 🚨 **Keep your GitHub credentials private.** Never share your GitHub password or any personal access tokens in Slack, email, or any document.

---

### Phase 3 — Python Environment

Python needs an isolated workspace for this project's tools so they do not conflict with other software on your computer.

> 💡 **What is a virtual environment?** Imagine a clean room specifically for this project. When you "activate" it, you are stepping into that room. All commands you run use only the tools inside that room.

**Step 1:** In VS Code, open a terminal: go to **Terminal → New Terminal** (the terminal panel appears at the bottom of VS Code).

**Step 2:** Create the virtual environment:
```
python -m venv .venv
```

**Step 3:** Activate it:
- **Mac/Linux:**
  ```
  source .venv/bin/activate
  ```
- **Windows:**
  ```
  .venv\Scripts\activate
  ```

You will see `(.venv)` appear at the start of the terminal line. That means it is active.

**Step 4:** Install all project dependencies:
```
pip install -r requirements.txt
```

This downloads and installs about 15 packages. It will take 1–3 minutes. Wait for it to finish.

> ⚠️ **Always activate the environment first.** Every time you open VS Code to use this system, run the `source .venv/bin/activate` (Mac) or `.venv\Scripts\activate` (Windows) command before running anything else. If you forget, commands will fail with confusing error messages.

**Checkpoint:** You should see a long list of "Successfully installed..." messages in the terminal. No red error text.

---

### Phase 4 — API Credentials (.env)

The `.env` file holds the passwords and API keys for every external service the system uses. It never leaves your computer and is never uploaded to GitHub.

**Step 1:** In VS Code's file explorer (left panel), find the file `.env.example` in the project root.

> 💡 **You may not see files starting with a dot by default.** On Mac, press `Cmd + Shift + .` in Finder to show hidden files. In VS Code, they are usually visible in the file panel.

**Step 2:** Make a copy of `.env.example` and rename the copy to `.env` (remove the `.example` part).

**Step 3:** Open `.env` and fill in the values for Superprof US. Use the table below as your guide:

| Variable | What It Is | Where to Find It |
|---|---|---|
| `DATAFORSEO_LOGIN` | Your DataForSEO account email | DataForSEO dashboard → Account → API credentials |
| `DATAFORSEO_PASSWORD` | Your DataForSEO API password | Same location |
| `WP_SUPERPROF_US_URL` | The Superprof US WordPress blog URL | Provided by your technical contact |
| `WP_SUPERPROF_US_USER` | Your WordPress admin username | Your WP admin login |
| `WP_SUPERPROF_US_APP_PASSWORD` | WordPress Application Password | See Phase 6 below |

Add these lines to your `.env` file:
```
# Superprof US WordPress API
WP_SUPERPROF_US_URL=[YOUR_WP_BLOG_URL]
WP_SUPERPROF_US_USER=[YOUR_WP_USERNAME]
WP_SUPERPROF_US_APP_PASSWORD=[YOUR_WP_APP_PASSWORD]
```

> 🚨 **Your .env file is a secret — treat it like a password.** Never paste its contents into Slack, email, or any document. Never commit it to GitHub (the `.gitignore` file prevents this automatically, but the responsibility is yours to keep the file private on your computer).

---

### Phase 5 — Google Service Account, Sheets, and Search Console

The system needs to read Google Search Console data and update Google Sheets on your behalf. To do this without requiring you to log in every time, it uses a **Service Account** — a special automated Google identity.

---

**Sub-task A: Create a Google Service Account**

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in with your Google account
2. At the top, click **Select a project → New Project**
   - Name it something like `superprof-content-writer`
   - Click **Create**
3. Enable the two required APIs:
   - In the left menu, go to **APIs & Services → Library**
   - Search for **Google Search Console API** → click it → click **Enable**
   - Go back to Library, search for **Google Sheets API** → click it → click **Enable**
4. Create the Service Account:
   - Go to **APIs & Services → Credentials**
   - Click **Create Credentials → Service Account**
   - Give it a name like `content-writer-bot`
   - Click **Create and Continue**, then **Done** (skip optional role assignments)
5. Download the JSON key:
   - In the Credentials page, click on the service account you just created
   - Go to the **Keys** tab
   - Click **Add Key → Create new key → JSON → Create**
   - A `.json` file downloads automatically — **do not rename it**

6. Save the file at this exact path on your computer:
   - **Mac:** Create folders if they don't exist, then place the file at:
     `~/.credentials/google/google-service-account.json`
     (In Terminal: `mkdir -p ~/.credentials/google` then move the file there)
   - **Windows:**
     `C:\Users\[your-username]\.credentials\google\google-service-account.json`

7. Note down the **service account email address** — it looks like:
   `content-writer-bot@superprof-content-writer.iam.gserviceaccount.com`
   You will need it in the next two sub-tasks.

> ⚠️ **Your service account JSON file is a credential.** Store it only at the path above. Do not email it, share it in Slack, or store it in the project folder (it would be excluded by `.gitignore` but it is better to keep credentials outside the project).

---

**Sub-task B: Share the Superprof US Google Sheets File**

1. Open the Superprof US tracking spreadsheet in Google Sheets
2. Click **Share** (top right corner)
3. In the "Add people and groups" field, paste the service account email from Sub-task A Step 7
4. Set permission to **Editor**
5. Uncheck **Notify people** (it cannot receive emails) → click **Share**

> 💡 **How to find a Google Sheets file ID:** Look at the URL of the spreadsheet. It looks like:
> `https://docs.google.com/spreadsheets/d/[THIS_LONG_STRING]/edit`
> The long string between `/d/` and `/edit` is the Spreadsheet ID. You will need it in Phase 7.

---

**Sub-task C: Add the Service Account to Google Search Console**

1. Go to [search.google.com/search-console](https://search.google.com/search-console)
2. Select the Superprof US property from the dropdown
3. Go to **Settings → Users and permissions → Add user**
4. Enter the service account email → set permission to **Full** → click **Add**

> ℹ️ **No GSC access?** If you cannot see the Superprof US property or do not have permission to add users, ask your technical contact to do this step for you.

---

### Phase 6 — WordPress Application Password

WordPress allows external tools to authenticate without your main password using a dedicated "Application Password."

1. Log in to the Superprof US WordPress admin panel
2. Go to **Users → Your Profile** (or **Users → All Users** → click your username)
3. Scroll down to the **Application Passwords** section
4. In the "New Application Password Name" field, type: `Content Writer Bot`
5. Click **Add New Application Password**
6. **Copy the generated password immediately** — WordPress shows it only once

Paste this password as the value of `WP_SUPERPROF_US_APP_PASSWORD` in your `.env` file.

> ⚠️ **Copy the password right away.** If you close the page without copying it, WordPress will not show it again. You would need to delete it and create a new one.

---

### Phase 7 — Register Superprof US in the Project

The project needs to know the Superprof US blog exists — its URL, its Google Sheets ID, and its settings. This is a one-time configuration step.

> ⚠️ **JSON is sensitive to typos.** A missing comma or quote in a JSON file can prevent the system from starting. If you are unsure about any value, ask your technical contact to review the file before saving.

**Step 1: Add Superprof US to `_shared/config/sites.json`**

Open `_shared/config/sites.json` in VS Code. Add a new entry inside the `"sites": [...]` array, after the last entry and before the closing `]`. Use this template (replace all `[YOUR_...]` placeholders with real values):

```json
{
  "id": "superprof-us",
  "name": "Superprof US",
  "domain": "superprof.com",
  "url_base": "https://www.superprof.com/blog/",
  "gsc_property": "https://www.superprof.com/blog/",
  "sheet_id": "[YOUR_SPREADSHEET_ID]",
  "credentials": "google-service-account.json",
  "active": true,
  "subject_category": "education_general",
  "content_type": "blog_article",
  "language": "en"
}
```

**Step 2: Create `_shared/config/blogs/superprof-us.json`**

Create a new file at that path. Paste the following and fill in the `[YOUR_...]` placeholders:

```json
{
  "blog_id": "superprof-us",
  "display_name": "Superprof US",
  "domain": "superprof.com",
  "url_base": "https://www.superprof.com/blog/",
  "gsc_property": "https://www.superprof.com/blog/",
  "gsc_credentials_filename": "google-service-account.json",

  "content_type": "blog_article",
  "subject_category": "education_general",
  "language": "en",

  "seo_settings": {
    "min_word_count": 1200,
    "max_word_count": 2000
  },

  "refresh_thresholds": {
    "stale_months": 12,
    "critical_months": 18,
    "ctr_low_threshold": 2.0,
    "impression_high_threshold": 1000
  },

  "sheets_config": {
    "spreadsheet_id": "[YOUR_SPREADSHEET_ID]",
    "spreadsheet_name": "Superprof US Articles",
    "main_sheet": "Growing"
  },

  "scraping_config": {
    "article_body": "article.post-content, article.entry-content, .post-content, .entry-content",
    "timeout": 30,
    "requires_playwright": false
  },

  "wp_api_config": {
    "api_base_url": "[YOUR_WP_BLOG_URL]/wp-json/wp/v2",
    "user_env_var": "WP_SUPERPROF_US_USER",
    "password_env_var": "WP_SUPERPROF_US_APP_PASSWORD",
    "timeout": 30
  }
}
```

---

### Phase 8 — Verify Everything Works

With the virtual environment activated, run:

```
python content_writer.py --help
```

You should see a list of available commands (`refresh`, `workflow`, `batch`, `audit`, `debug`, etc.). If you see this, the core installation is working.

Then test your Superprof US configuration:

```
python content_writer.py debug config --blog superprof-us
```

This prints the loaded configuration for the `superprof-us` blog. If you see your configuration details, Phase 7 was done correctly.

> ⚠️ **If you see `ModuleNotFoundError`:** The virtual environment is not activated. Run `source .venv/bin/activate` (Mac) or `.venv\Scripts\activate` (Windows) and try again.

> ⚠️ **If you see `blog_id not found`:** The `superprof-us` entry was not saved correctly in `_shared/config/sites.json`. Re-check the file for JSON syntax errors (missing commas, unclosed brackets).

---

## PART 3 — Your Project Files — A Quick Tour

You do not need to memorize the whole project. Here is the map of what matters.

### Files You Will Use Regularly

| File or Folder | What It Is |
|---|---|
| `.env` | Your private credentials file. You fill this in once and rarely change it. |
| `_shared/outputs/superprof-us/html/` | Where the finished article HTML files are saved after a refresh. You copy from here into WordPress. |
| `_shared/outputs/superprof-us/metadata/` | JSON files with the SEO title, meta description, and keywords for each refreshed article. |
| `_shared/config/blogs/superprof-us.json` | The Superprof US blog settings (WP API, sheet ID, word count targets). |

### Files You Should Know Exist — But Not Edit

| File or Folder | Why Not to Edit It |
|---|---|
| `CLAUDE.md` | The AI's editorial rulebook. Changes affect all content generation. Only edit with approval. |
| `scripts/` | All Python automation. Editing requires developer testing. |
| `_shared/config/sites.json` | The blog registry. Editing incorrectly breaks all blog lookups. |
| `.gitignore` | Ensures private files (like `.env`) are never uploaded to GitHub. Never edit. |
| `requirements.txt` | Python package manifest. Never edit manually. |

### Files for Reference Only (You Do Not Need to Read These to Use the System)

| File | What It Is |
|---|---|
| `_shared/docs/STYLE_GUIDE.md` | Editorial anti-patterns Claude is trained to avoid |
| `_shared/docs/EEAT_GUIDE.md` | Expertise, Authority, and Trust guidelines built into the prompts |
| `README.md` | Technical project documentation for developers |

> ℹ️ **The editorial guidelines in `_shared/docs/` and `_shared/prompts/` are already baked into how Claude writes.** You do not need to read them to get good output. They exist if you ever want to understand a specific editorial decision Claude made.

---

## PART 4 — Claude Code Modes

Claude Code has three operating modes that control how much it asks before making changes.

### Plan Mode — Safest for Exploration

Claude reads files, analyzes the situation, and writes out what it intends to do — but **asks your permission before making any changes**. Use this when you are learning the system or want to preview what will happen before it runs.

### Ask Before Edit — Recommended for Daily Work

Claude drafts any file changes and shows them to you as a diff (before vs. after view) before applying them. You approve or reject each change. This is the right mode for production work.

### Edit Automatically — Use Only When Confident

Claude applies changes without asking. Only use this for well-understood, repetitive steps where you have already seen the output many times and trust the pattern.

> ⚠️ **Use Ask Before Edit until you are comfortable.** It adds one approval click per change, but it means you always review what Claude is about to do. You can switch to Edit Automatically later once you know the workflow well.

**How to switch modes:** The mode selector is in the Claude Code panel in VS Code. You will see the three options when you open the chat panel.

---

## PART 5 — The 7-Step Content Refresh Workflow

This is your core daily task. The workflow turns a stale article URL into a refreshed, ready-to-publish HTML file.

### Before You Start: The Google Sheets Control Panel

Your Google Sheets file is the source of truth for all article work. Each row is one article URL. The key columns to know:

| Column | Name | What It Means |
|---|---|---|
| A | `blog_id` | Should be `superprof-us` for all your articles |
| B | `blogpost_url` | The article URL — the unique identifier for each row |
| C | `main_keyword` | The primary keyword this article targets |
| F | `action_blogpost` | What the system decided the article needs: `NO ACTION`, `TITLE OPTIMIZATION`, `PARTIAL REFRESH`, `FULL REFRESH` |
| G | `status` | Where the article is in the workflow: `TODO`, `Rédigé`, `BLOCKED` |

> ℹ️ **Google Sheets is your source of truth.** Always check the sheet before starting work on any article. The system also writes results back to the sheet automatically after each step.

---

### Step 0 — Keyword Discovery (if needed)

**What it does:** Fills in missing `main_keyword` values for articles that do not have one yet.

**When to run it:** Before auditing. If an article row has no keyword in column C, the audit step cannot run properly.

**How to do it:** You can fill keywords manually in column C of the spreadsheet. For a batch of articles, you can also ask Claude to suggest keywords based on the article URLs:

```
python content_writer.py batch keyword-discovery --blog superprof-us
```

**What success looks like:** Every row that you plan to refresh has a value in the `main_keyword` column.

---

### Step 1 — Ingest (Fetch Current Article Content)

**What it does:** The system connects to WordPress via its REST API and downloads the current HTML of the article. This is the source material for the refresh — no manual copying needed.

**When it runs:** This step runs automatically as part of the full workflow (Step 5). You do not need to run it separately unless debugging.

**What success looks like:** A folder named after the article slug appears inside `_shared/context/`. It contains the original HTML and audit data.

---

### Step 2 — GSC Audit (Pull Google Search Console Data)

**What it does:** Connects to Google Search Console and pulls the last 30 days of performance data for each article — impressions, clicks, CTR, average position — and writes it to the Google Sheets columns.

**How to run it (for a batch of articles):**
```
python content_writer.py batch audit-gsc --blog superprof-us
```

**What success looks like:** The impressions, clicks, CTR, and position columns in your Sheets are filled with numbers for each article.

---

### Step 3 — SERP Audit (Pull Competitor Data)

**What it does:** Uses DataForSEO to look at what the top-ranking pages look like for each article's keyword — how long they are, how they are structured, and what "People Also Ask" questions appear. This informs what the refreshed article should include.

**How to run it:**
```
python content_writer.py batch audit-serp --blog superprof-us
```

**What success looks like:** The SERP and PAA (People Also Ask) columns in Sheets are filled.

---

### Step 4 — Decision (What Does Each Article Need?)

**What it does:** The system reads all the GSC and SERP data for each article and automatically assigns it a recommended action. The action appears in the `action_blogpost` column (column F) of your Sheets.

| Action | What It Means |
|---|---|
| `NO ACTION` | The article is performing well — nothing to do right now |
| `TITLE OPTIMIZATION` | Only the title and meta description need refreshing |
| `PARTIAL REFRESH` | Some sections have outdated data or stats — update those |
| `FULL REFRESH` | The article needs a complete rewrite |
| `SEMANTIC REORIENTATION` | The keyword focus needs to shift based on new search trends |

**How to run it:**
```
python content_writer.py batch decision --blog superprof-us
```

**What success looks like:** Column F is populated for all rows. You can review the recommendations and decide which ones to act on.

> 💡 **You can override the system's decision.** If you disagree with the action assigned to a specific article, you can manually edit column F in Google Sheets before running content generation. The system will use whatever value is in that cell.

---

### Step 5 — Content Generation (Claude Rewrites the Article)

**What it does:** This is the main step. Claude reads the original article HTML, the audit data, the editorial guidelines for Superprof US, and the competitor analysis, then writes a refreshed version. The output is saved as a Gutenberg-compatible HTML file.

This step takes 2–5 minutes per article depending on length.

**How to run it — for a single article (recommended when starting out):**
```
python content_writer.py refresh [ARTICLE_URL] --blog superprof-us
```

**For a batch of articles with the same action:**
```
python content_writer.py batch refresh --blog superprof-us --action FULL_REFRESH
```

**What success looks like:** A new file appears at:
`_shared/outputs/superprof-us/html/[article-slug]_refreshed.gutenberg.html`

And its SEO metadata at:
`_shared/outputs/superprof-us/metadata/[article-slug]_metadata.json`

> ⚠️ **Review the output before publishing.** Claude generates the HTML automatically, but you are the final quality gate. Open the output file and read it. Check that the article reads naturally, the information is accurate, and there are no obvious formatting issues. If something looks wrong, you can ask Claude to revise specific sections before publishing.

---

### Step 6 — Sync (Update Google Sheets)

**What it does:** Writes the results back to Google Sheets — word counts before and after, number of assets preserved, which strategy was applied, and the timestamp.

This step runs automatically at the end of the full workflow. You can also trigger it manually if needed.

**What success looks like:** The `status` column for the article shows `Rédigé` and the word count and asset columns are filled in.

---

## PART 6 — Publishing to WordPress

This is the manual step you perform after content generation. You copy the HTML output into WordPress and update the SEO metadata.

### The Two Output Files

For each refreshed article, two files are created:

| File | What It Contains | Where to Find It |
|---|---|---|
| `[slug]_refreshed.gutenberg.html` | The full article body, formatted for WordPress Gutenberg | `_shared/outputs/superprof-us/html/` |
| `[slug]_metadata.json` | SEO title, meta description, H1, and target keywords | `_shared/outputs/superprof-us/metadata/` |

---

### Step-by-Step: Copy the HTML into WordPress

1. Open `[slug]_refreshed.gutenberg.html` in VS Code
2. Select all the content: `Cmd + A` (Mac) or `Ctrl + A` (Windows)
3. Copy: `Cmd + C` (Mac) or `Ctrl + C` (Windows)
4. Log in to the Superprof US WordPress admin panel
5. Find the article to update: **Posts → find by title or slug**
6. Open the article in the Gutenberg editor
7. Click the **three-dot menu** (top right, ⋮) → select **Code Editor**
8. Select all existing content in the code editor (`Ctrl + A` / `Cmd + A`) and **delete it**
9. Paste your copied HTML (`Ctrl + V` / `Cmd + V`)
10. Click **Visual Editor** to return to normal view and check the layout

> ⚠️ **Always paste in Code Editor, not Visual Editor.** Pasting HTML directly into the visual editor will break the formatting — WordPress will treat the HTML tags as plain text. Always switch to Code Editor first, paste there, then switch back to Visual Editor to review.

---

### Fill In the SEO Metadata

1. Open `[slug]_metadata.json` in VS Code
2. Find the `"title"` value — this is the **SEO page title** (what appears in Google results and the browser tab). Enter it in your SEO plugin's Title field (e.g., Yoast SEO or RankMath).
3. Find `"meta_description"` — enter it in the SEO plugin's Meta Description field.
4. The `"h1"` value is already inside the HTML you pasted. You do not need to add it again.

> 💡 **The title and the H1 are intentionally different.** The `title` (in the metadata file) is optimized for search results — concise, keyword-forward. The `h1` (inside the article) is the editorial headline — more expressive. Use the `title` value for your SEO plugin. Do not create a second H1 in WordPress.

---

### Pre-Publish Checklist

Before clicking **Update**:

- [ ] The article reads naturally from start to finish
- [ ] Images are visible and correctly placed (no broken image placeholders)
- [ ] Spot-check 2–3 links to confirm they open correctly
- [ ] SEO title is set (60 characters max)
- [ ] Meta description is set (150–155 characters)
- [ ] No duplicate H1 visible on the page
- [ ] WordPress shows no red errors in the editor

---

### After Publishing

1. Confirm the article's `status` column in Google Sheets shows `Rédigé` (the system should have set this in Step 6; if not, update it manually)
2. Do not refresh the same article again for at least 4 weeks — Google needs time to re-crawl and re-evaluate the page

---

## PART 7 — Troubleshooting

---

**`ModuleNotFoundError` when running a command**

Cause: The virtual environment is not activated.

Fix: Run `source .venv/bin/activate` (Mac) or `.venv\Scripts\activate` (Windows) in the VS Code terminal. Look for `(.venv)` at the start of the terminal line to confirm it is active.

---

**"Spreadsheet not found" or "Permission denied" on Google Sheets**

Cause: Either the service account email does not have access to the spreadsheet, or the `spreadsheet_id` in `_shared/config/blogs/superprof-us.json` is wrong.

Fix:
1. Open the Google Sheets file and click Share — confirm the service account email has Editor access.
2. Check the `sheet_id` value in the blog config. Compare it against the ID in the spreadsheet URL.

---

**"401 Unauthorized" on WordPress (during ingest or writing)**

Cause: The `WP_SUPERPROF_US_APP_PASSWORD` value in your `.env` file is incorrect or has expired.

Fix: In WordPress Admin, go to Users → Your Profile → Application Passwords. Delete the existing `Content Writer Bot` password and create a new one. Copy it carefully — including the spaces. Paste it into `.env`.

---

**DataForSEO errors (no SERP data, authentication failed)**

Cause: The `DATAFORSEO_LOGIN` or `DATAFORSEO_PASSWORD` in `.env` is incorrect, or your account has run out of API credits.

Fix: Check your credentials at [dataforseo.com](https://dataforseo.com) under Account → API credentials. Also verify your credit balance on the same page.

---

**Output HTML file is empty or unexpectedly short**

Cause: The ingest step (Step 1) did not successfully fetch the article content from WordPress.

Fix: Re-run the full workflow for that article. If it fails again, check that the WordPress Application Password is correctly set in `.env` and that the `api_base_url` in `superprof-us.json` is correct.

---

**`blog_id 'superprof-us' not found`**

Cause: The `superprof-us` entry was not saved correctly in `_shared/config/sites.json`, or there is a JSON syntax error.

Fix: Open `_shared/config/sites.json` in VS Code. Check that the `"id": "superprof-us"` entry is present and that the JSON is valid (no missing commas, properly closed brackets). VS Code highlights JSON errors in red.

---

**Claude Code extension is not responding**

Cause: You are not signed in to your Anthropic account in VS Code, or there is a temporary service interruption.

Fix: Click the Claude icon in the VS Code sidebar and confirm you are signed in. If signed in and still failing, check [status.anthropic.com](https://status.anthropic.com) for any ongoing issues.

---

> ⚠️ **When in doubt, ask before trying multiple things.** If you see an error you do not recognize, take a screenshot and send it to your technical contact before experimenting with fixes. Random changes can make the underlying problem harder to diagnose.

---

## PART 8 — Quick Reference Card

### Key Commands

| What You Want to Do | Command |
|---|---|
| Check the system is working | `python content_writer.py --help` |
| Verify Superprof US config loads | `python content_writer.py debug config --blog superprof-us` |
| Discover missing keywords | `python content_writer.py batch keyword-discovery --blog superprof-us` |
| Pull GSC data for all articles | `python content_writer.py batch audit-gsc --blog superprof-us` |
| Pull SERP data for all articles | `python content_writer.py batch audit-serp --blog superprof-us` |
| Run the decision engine | `python content_writer.py batch decision --blog superprof-us` |
| Refresh one article | `python content_writer.py refresh [URL] --blog superprof-us` |
| Batch refresh all FULL_REFRESH articles | `python content_writer.py batch refresh --blog superprof-us --action FULL_REFRESH` |

> 💡 **Before any command:** Make sure your virtual environment is active. You should see `(.venv)` at the start of the terminal line.

---

### Key File Paths

| What | Path |
|---|---|
| Your credentials | `.env` (project root) |
| Service account JSON | `~/.credentials/google/google-service-account.json` |
| Blog registry | `_shared/config/sites.json` |
| Superprof US blog config | `_shared/config/blogs/superprof-us.json` |
| Refreshed HTML outputs | `_shared/outputs/superprof-us/html/` |
| SEO metadata outputs | `_shared/outputs/superprof-us/metadata/` |
| AI editorial rulebook (read-only) | `CLAUDE.md` |

---

### Refresh Actions Explained

| Action | What Happens |
|---|---|
| `NO ACTION` | Article is performing well — skip it for now |
| `TITLE OPTIMIZATION` | Only the title and meta description are rewritten |
| `PARTIAL REFRESH` | Outdated sections, stats, or data are updated |
| `FULL REFRESH` | The entire article is rewritten |
| `SEMANTIC REORIENTATION` | The article is restructured around a new primary keyword |

---

### Contacts

| Role | Name | How to Reach |
|---|---|---|
| Technical issues (errors, setup) | [Developer name] | [Slack / email] |
| Editorial / content questions | [SEO Lead] | [Slack / email] |
| WordPress admin access | [WP admin contact] | [Slack / email] |
| Google Cloud / GSC access | [Google admin contact] | [Slack / email] |
