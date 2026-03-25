# Browser Automation with Playwright: Beyond Testing

When most developers hear "Playwright," they think end-to-end testing. And yes, Playwright is excellent for testing. But limiting it to tests is like using a Swiss Army knife only as a bottle opener.

Playwright is a **full browser automation platform** — and once you start using it for tasks beyond testing, you'll wonder how you ever lived without it.

## Why Playwright for Non-Testing Automation?

The browser automation landscape in 2026 looks like this:

| Tool | Strengths | Weaknesses |
|------|-----------|------------|
| curl/httpx | Fast, simple | No JavaScript rendering |
| Puppeteer | Good Chrome support | Chrome only, API churn |
| Selenium | Wide browser support | Slow, flaky, verbose |
| **Playwright** | Multi-browser, fast, modern API | Heavier than curl |

Playwright wins for any automation that needs:
- JavaScript rendering (SPAs, dynamic content)
- Authentication flows (login, OAuth, 2FA)
- Complex interaction sequences (click, fill, drag, upload)
- Reliable waiting and retry mechanisms
- Multi-page workflows

## Use Case 1: Data Collection from Dynamic Sites

Many valuable data sources are SPAs with no API. Playwright handles them effortlessly:

```typescript
import { chromium } from 'playwright';

async function collectPricingData() {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    await page.goto('https://competitor.com/pricing');
    await page.waitForSelector('.pricing-card');
    
    const plans = await page.$$eval('.pricing-card', cards =>
        cards.map(card => ({
            name: card.querySelector('.plan-name')?.textContent?.trim(),
            price: card.querySelector('.price')?.textContent?.trim(),
            features: Array.from(card.querySelectorAll('.feature'))
                .map(f => f.textContent?.trim())
        }))
    );

    await browser.close();
    return plans;
}
```

### Handling Authentication

Most real-world scraping requires login. Playwright's persistent contexts make this painless:

```typescript
async function authenticatedSession() {
    const context = await chromium.launchPersistentContext(
        './browser-data',
        { headless: true }
    );
    const page = context.pages()[0] || await context.newPage();

    await page.goto('https://app.example.com/dashboard');

    if (page.url().includes('/login')) {
        await page.fill('#email', process.env.EMAIL!);
        await page.fill('#password', process.env.PASSWORD!);
        await page.click('button[type="submit"]');
        await page.waitForURL('**/dashboard');
    }

    const data = await page.evaluate(() => {
        return document.querySelector('.dashboard-stats')?.textContent;
    });

    await context.close();
    return data;
}
```

## Use Case 2: Workflow Automation

Automate repetitive web workflows that don't have APIs:

```typescript
async function submitExpenseReport(expenses: Expense[]) {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    await page.goto('https://expenses.company.com');
    await page.fill('#username', process.env.EXPENSE_USER!);
    await page.fill('#password', process.env.EXPENSE_PASS!);
    await page.click('#login-btn');
    await page.waitForURL('**/dashboard');

    await page.click('text=New Expense Report');
    await page.fill('#report-title',
        `Expenses ${new Date().toISOString().slice(0, 7)}`);

    for (const expense of expenses) {
        await page.click('text=Add Expense');
        await page.fill('#amount', expense.amount.toString());
        await page.fill('#description', expense.description);
        await page.selectOption('#category', expense.category);

        if (expense.receiptPath) {
            const fileInput = page.locator('input[type="file"]');
            await fileInput.setInputFiles(expense.receiptPath);
        }

        await page.click('text=Save Expense');
        await page.waitForSelector('.expense-saved-toast');
    }

    await page.click('text=Submit for Approval');
    await page.click('text=Confirm');

    const confirmationId = await page
        .locator('.confirmation-id')
        .textContent();

    await browser.close();
    return confirmationId;
}
```

## Use Case 3: Visual Monitoring and Alerts

Monitor web pages for visual changes:

```typescript
async function monitorPageChanges(url: string, name: string) {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle' });

    const screenshotPath = `./monitoring/${name}-latest.png`;
    const previousPath = `./monitoring/${name}-previous.png`;

    if (fs.existsSync(screenshotPath)) {
        fs.copyFileSync(screenshotPath, previousPath);
    }

    await page.screenshot({ path: screenshotPath, fullPage: true });

    const currentContent = await page.evaluate(() =>
        document.body.innerText
    );

    const currentHash = Buffer
        .from(currentContent)
        .toString('base64')
        .slice(0, 32);

    // Compare with previous hash to detect changes
    let changed = false;
    const hashPath = `./monitoring/${name}-hash.txt`;
    if (fs.existsSync(hashPath)) {
        const previousHash = fs.readFileSync(hashPath, 'utf-8');
        changed = currentHash !== previousHash;
    }

    fs.writeFileSync(hashPath, currentHash);
    await browser.close();

    if (changed) {
        console.log(`⚠️ Change detected on ${name}!`);
        await sendAlert(name, url);
    }
}
```

## Use Case 4: PDF Generation from Web Content

Generate professional PDFs from HTML:

```typescript
async function generateInvoicePdf(invoiceData: Invoice) {
    const browser = await chromium.launch();
    const page = await browser.newPage();

    await page.goto('file:///templates/invoice.html');

    await page.evaluate((data) => {
        document.getElementById('invoice-number')!
            .textContent = data.number;
        document.getElementById('client-name')!
            .textContent = data.clientName;
        document.getElementById('total')!
            .textContent = `$${data.total.toFixed(2)}`;
    }, invoiceData);

    await page.pdf({
        path: `./invoices/${invoiceData.number}.pdf`,
        format: 'A4',
        margin: { top: '1cm', bottom: '1cm', left: '1cm', right: '1cm' },
        printBackground: true
    });

    await browser.close();
}
```

## Production Tips

### Run Headless in Docker

```dockerfile
FROM mcr.microsoft.com/playwright:v1.50.0-noble
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["node", "automation.js"]
```

### Handle Flakiness

```typescript
async function withRetry<T>(
    fn: () => Promise<T>,
    maxRetries = 3
): Promise<T> {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            console.log(`Retry ${i + 1}/${maxRetries}...`);
            await new Promise(r => setTimeout(r, 2000 * (i + 1)));
        }
    }
    throw new Error("Unreachable");
}
```

### Be a Good Citizen

```typescript
// Add delays between actions
await page.waitForTimeout(1000 + Math.random() * 2000);

// Set a reasonable user agent
const context = await browser.newContext({
    userAgent: 'MyBot/1.0 (automation; contact@example.com)'
});

// Respect robots.txt. Honor rate limits. Cache results.
```

## The Bottom Line

Playwright is a general-purpose browser automation platform that happens to be excellent at testing. Once you start seeing the browser as a programmable interface to the web, automation opportunities appear everywhere.

Start with one repetitive web task you do manually. Automate it with Playwright. Then look for the next one. Before you know it, you'll have reclaimed hours every week.

---

*Want to learn more about automating your entire development workflow?* Check out **[AI-Powered Development: From Copilot to Full Agent Teams](https://gumroad.com/l/ai-powered-dev)** — includes hands-on modules on building automation agents. **Early bird: $9.99** (regular $19.99).

*Follow Content Empire on [Medium](https://medium.com/@contentempire) for more developer productivity guides.*

**Tags: #Playwright #Automation #WebScraping #Productivity #Programming #Tools #JavaScript #DevOps**
