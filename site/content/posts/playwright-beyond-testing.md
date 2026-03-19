---
title: "Browser Automation with Playwright: Beyond Testing"
date: 2025-07-27
author: "The Content Empire Team"
tags: ["Playwright", "automation", "scraping", "productivity", "tools"]
description: "Playwright isn't just for testing — it's a powerful automation platform. From web scraping to workflow automation to monitoring, here's how to use Playwright for everything."
---

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
    
    // Wait for the dynamic pricing table to load
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

// Run daily to track pricing changes
const pricing = await collectPricingData();
console.table(pricing);
```

### Handling Authentication

Most real-world scraping requires login. Playwright's persistent contexts make this painless:

```typescript
import { chromium } from 'playwright';

async function authenticatedSession() {
    const context = await chromium.launchPersistentContext(
        './browser-data', // Stores cookies, localStorage, etc.
        { headless: true }
    );
    const page = context.pages()[0] || await context.newPage();
    
    // Check if already logged in
    await page.goto('https://app.example.com/dashboard');
    
    if (page.url().includes('/login')) {
        // Need to log in
        await page.fill('#email', process.env.EMAIL!);
        await page.fill('#password', process.env.PASSWORD!);
        await page.click('button[type="submit"]');
        await page.waitForURL('**/dashboard');
    }
    
    // Now authenticated — do your work
    const data = await page.evaluate(() => {
        // Extract data from the authenticated page
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
    
    // Login to expense system
    await page.goto('https://expenses.company.com');
    await page.fill('#username', process.env.EXPENSE_USER!);
    await page.fill('#password', process.env.EXPENSE_PASS!);
    await page.click('#login-btn');
    await page.waitForURL('**/dashboard');
    
    // Create new report
    await page.click('text=New Expense Report');
    await page.fill('#report-title', 
        `Expenses ${new Date().toISOString().slice(0, 7)}`);
    
    for (const expense of expenses) {
        await page.click('text=Add Expense');
        await page.fill('#amount', expense.amount.toString());
        await page.fill('#description', expense.description);
        await page.selectOption('#category', expense.category);
        
        // Upload receipt
        if (expense.receiptPath) {
            const fileInput = page.locator('input[type="file"]');
            await fileInput.setInputFiles(expense.receiptPath);
        }
        
        await page.click('text=Save Expense');
        await page.waitForSelector('.expense-saved-toast');
    }
    
    // Submit the report
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
import { chromium } from 'playwright';
import * as fs from 'fs';

async function monitorPageChanges(url: string, name: string) {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle' });
    
    const screenshotPath = `./monitoring/${name}-latest.png`;
    const previousPath = `./monitoring/${name}-previous.png`;
    
    // Save previous screenshot for comparison
    if (fs.existsSync(screenshotPath)) {
        fs.copyFileSync(screenshotPath, previousPath);
    }
    
    // Take new screenshot
    await page.screenshot({ 
        path: screenshotPath, 
        fullPage: true 
    });
    
    // Check for specific content changes
    const currentContent = await page.evaluate(() => 
        document.body.innerText
    );
    
    const hashPath = `./monitoring/${name}-hash.txt`;
    const currentHash = Buffer
        .from(currentContent)
        .toString('base64')
        .slice(0, 32);
    
    let changed = false;
    if (fs.existsSync(hashPath)) {
        const previousHash = fs.readFileSync(hashPath, 'utf-8');
        changed = currentHash !== previousHash;
    }
    
    fs.writeFileSync(hashPath, currentHash);
    await browser.close();
    
    if (changed) {
        console.log(`⚠️ Change detected on ${name}!`);
        await sendAlert(name, url);
    } else {
        console.log(`✅ No changes on ${name}`);
    }
}

// Monitor competitor pricing pages, status pages, etc.
await monitorPageChanges(
    'https://competitor.com/pricing', 
    'competitor-pricing'
);
```

## Use Case 4: PDF Generation from Web Content

Generate professional PDFs from HTML/web content:

```typescript
async function generateInvoicePdf(invoiceData: Invoice) {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    // Load the invoice template
    await page.goto('file:///templates/invoice.html');
    
    // Populate the template
    await page.evaluate((data) => {
        document.getElementById('invoice-number')!
            .textContent = data.number;
        document.getElementById('client-name')!
            .textContent = data.clientName;
        document.getElementById('total')!
            .textContent = `$${data.total.toFixed(2)}`;
        
        const tbody = document.getElementById('line-items')!;
        for (const item of data.items) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.description}</td>
                <td>${item.quantity}</td>
                <td>$${item.unitPrice.toFixed(2)}</td>
                <td>$${(item.quantity * item.unitPrice).toFixed(2)}</td>
            `;
            tbody.appendChild(row);
        }
    }, invoiceData);
    
    // Generate PDF
    const pdfPath = `./invoices/${invoiceData.number}.pdf`;
    await page.pdf({
        path: pdfPath,
        format: 'A4',
        margin: { top: '1cm', bottom: '1cm', left: '1cm', right: '1cm' },
        printBackground: true
    });
    
    await browser.close();
    return pdfPath;
}
```

## Use Case 5: API Testing with Browser Context

Some APIs require browser cookies or CSRF tokens. Playwright can handle the authentication dance:

```typescript
async function callAuthenticatedApi(endpoint: string) {
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    
    // Authenticate through the browser
    await page.goto('https://app.example.com/login');
    await page.fill('#email', process.env.EMAIL!);
    await page.fill('#password', process.env.PASSWORD!);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard');
    
    // Now use the authenticated context for API calls
    const response = await context.request.get(
        `https://api.example.com${endpoint}`,
        {
            headers: {
                'Accept': 'application/json'
            }
        }
    );
    
    const data = await response.json();
    await browser.close();
    return data;
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
// Use built-in retry and timeout mechanisms
await page.click('button.submit', { timeout: 10_000 });
await page.waitForResponse(
    resp => resp.url().includes('/api/') && resp.status() === 200,
    { timeout: 30_000 }
);

// Retry the entire operation on failure
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
// Add delays between actions to avoid hammering servers
await page.waitForTimeout(1000 + Math.random() * 2000);

// Set a reasonable user agent
const context = await browser.newContext({
    userAgent: 'MyBot/1.0 (automation; contact@example.com)'
});

// Respect robots.txt (check before scraping)
// Honor rate limits
// Cache results to minimize requests
```

## The Bottom Line

Playwright is a general-purpose browser automation platform that happens to be excellent at testing. Once you start seeing the browser as a programmable interface to the web, automation opportunities appear everywhere.

Start with one repetitive web task you do manually. Automate it with Playwright. Then look for the next one. Before you know it, you'll have reclaimed hours every week.

---

*Content Empire explores developer tools for maximum productivity. Follow for practical automation guides.*
