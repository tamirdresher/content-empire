#Requires -Version 7.0
<#
.SYNOPSIS
    Ralph (Badger) — Content Empire Goal-Driven Work Monitor
.DESCRIPTION
    Watches the content-empire repo for stale issues, open PRs,
    and pipeline health. Alerts when content cadence slips.
    GOAL-DRIVEN: Reads company objectives and auto-creates issues
    for any objective not yet tracked on the board.
#>

param(
    [string]$Owner = "tamirdresher",
    [string]$Repo  = "content-empire",
    [int]$StaleDays = 3,
    [switch]$Loop,
    [int]$IntervalMinutes = 60
)

# ── Company Objectives ────────────────────────────────────────────────────────
# These are the strategic goals for the Content Empire.
# Ralph will auto-create GitHub issues for any objective with no coverage.
$CompanyObjectives = @(
    @{ Key="gumroad-course";   Title="Launch AI-Powered Dev course on Gumroad (Early Bird \$9.99)";   Body="Publish the AI-Powered Development course on Gumroad. Early bird at `$9.99, full price `$19.99. See `monetization/gumroad-product-listing.md` for listing guide."; Labels="monetization,course" }
    @{ Key="github-sponsors";  Title="Set up GitHub Sponsors (3 tiers: \$5 / \$15 / \$50/mo)";        Body="Configure GitHub Sponsors with the 3 defined tiers in REVENUE_STRATEGY.md: Supporter `$5, Builder `$15, Empire Builder `$50."; Labels="monetization,community" }
    @{ Key="newsletter";       Title="Launch newsletter — target 500+ subscribers in 3 months";        Body="Set up Substack newsletter. First issue should ship within 2 weeks of launch. Growth target: 500 subscribers in 3 months per STATUS.md."; Labels="marketing,newsletter" }
    @{ Key="medium-publish";   Title="Publish 5 articles to Medium (follow PUBLISHING_CHECKLIST.md)";  Body="Publish all 5 medium-ready articles from medium-ready/ directory. Follow the staggered schedule in PUBLISHING_CHECKLIST.md."; Labels="content,medium" }
    @{ Key="devto-publish";    Title="Publish 3 articles to Dev.to";                                   Body="Publish the 3 devto-ready articles. See devto-ready/ directory and PUBLISHING_CHECKLIST.md for Dev.to publishing steps."; Labels="content,devto" }
    @{ Key="cheat-sheet";      Title="Create Prompt Engineering Cheat Sheet digital product (\$4.99)"; Body="Create and publish the Prompt Engineering Cheat Sheet on Gumroad at `$4.99. See REVENUE_STRATEGY.md section on digital products."; Labels="monetization,product" }
    @{ Key="independent-host"; Title="Deploy site to independent hosting (Netlify or Vercel)";         Body="Move off GitHub Pages to Netlify or Vercel for a custom domain, better SEO, and independent branding. Register content-empire domain."; Labels="infrastructure" }
    @{ Key="social-accounts";  Title="Create social media accounts (Dev.to, Medium, Hashnode, X)";     Body="Set up Content Empire brand accounts (NOT personal accounts). See social/profiles.md for details."; Labels="marketing,social" }
    @{ Key="medium-automation";Title="Automate Medium cross-posting via API";                           Body="Set up automated cross-posting from source articles to Medium. See brand/cross-posting-workflow.md for workflow design."; Labels="automation,medium" }
    @{ Key="digital-products"; Title="Create AI Development Toolkit digital product (\$14.99)";        Body="Create the AI Development Toolkit (templates + configs) at `$14.99 on Gumroad. See REVENUE_STRATEGY.md for full product spec."; Labels="monetization,product" }
)

function gh-p { gh auth switch --user tamirdresher 2>$null | Out-Null; gh @args }

function Get-StaleIssues {
    $cutoff = (Get-Date).AddDays(-$StaleDays).ToString("yyyy-MM-ddTHH:mm:ssZ")
    $issues = gh-p issue list --repo "$Owner/$Repo" --state open --json number,title,updatedAt,labels --limit 200 2>$null | ConvertFrom-Json
    $stale = $issues | Where-Object { $_.updatedAt -lt $cutoff }
    return $stale
}

function Get-OpenPRs {
    $prs = gh-p pr list --repo "$Owner/$Repo" --state open --json number,title,createdAt,author 2>$null | ConvertFrom-Json
    return $prs
}

function Get-ContentCadence {
    $sevenDaysAgo = (Get-Date).AddDays(-7).ToString("yyyy-MM-ddTHH:mm:ssZ")
    $recentClosed = gh-p issue list --repo "$Owner/$Repo" --state closed --json number,title,closedAt,labels --limit 100 2>$null | ConvertFrom-Json
    $thisWeek = $recentClosed | Where-Object { $_.closedAt -ge $sevenDaysAgo }
    return $thisWeek
}

# ── Goal Coverage Check ───────────────────────────────────────────────────────
function Get-GoalCoverage {
    <#
    Returns a list of objectives that have NO matching open or closed issue in
    the last 90 days. These are the gaps Ralph will fill.
    #>
    $allIssues = gh-p issue list --repo "$Owner/$Repo" --state all --json number,title,body,labels --limit 500 2>$null | ConvertFrom-Json
    $gaps = @()
    foreach ($obj in $CompanyObjectives) {
        # Match by key word in title (case-insensitive) — if any existing issue title
        # contains a distinctive keyword from the objective key, consider it covered
        $keyword = $obj.Key -replace '-', ' '
        $parts = $obj.Key -split '-' | Where-Object { $_.Length -gt 3 }
        $covered = $allIssues | Where-Object {
            $t = $_.title.ToLower()
            foreach ($part in $parts) { if ($t -like "*$part*") { return $true } }
            return $false
        }
        if (-not $covered) {
            $gaps += $obj
        }
    }
    return $gaps
}

function New-ObjectiveIssue {
    param($Obj)
    $labels = $Obj.Labels -replace ',', ' --label '
    Write-Host "    🆕 Creating issue: $($Obj.Title)" -ForegroundColor Green
    $result = gh-p issue create --repo "$Owner/$Repo" `
        --title $Obj.Title `
        --body $Obj.Body `
        --label "squad" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "       ✅ Created: $result" -ForegroundColor DarkGreen
        return $true
    } else {
        Write-Host "       ❌ Failed: $result" -ForegroundColor DarkRed
        return $false
    }
}

function Invoke-GoalCheck {
    Write-Host ""
    Write-Host "  🎯 OBJECTIVE COVERAGE CHECK:" -ForegroundColor Cyan
    $gaps = Get-GoalCoverage
    if ($gaps.Count -eq 0) {
        Write-Host "    ✅ All $($CompanyObjectives.Count) company objectives have issues — full coverage!" -ForegroundColor Green
    } else {
        Write-Host "    ⚠️  $($gaps.Count) objective(s) have NO tracking issue — creating them now:" -ForegroundColor Yellow
        $created = 0
        foreach ($gap in $gaps) {
            $ok = New-ObjectiveIssue -Obj $gap
            if ($ok) { $created++ }
            Start-Sleep -Milliseconds 500  # rate limit guard
        }
        Write-Host "    📋 Created $created new objective issue(s)" -ForegroundColor White
    }
}

function Write-Report {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  🦡 RALPH (BADGER) — Content Empire Monitor" -ForegroundColor Yellow
    Write-Host "  $timestamp" -ForegroundColor DarkGray
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Yellow

    # Goal coverage — the key new behavior
    Invoke-GoalCheck

    # Stale issues
    $stale = Get-StaleIssues
    if ($stale.Count -gt 0) {
        Write-Host ""
        Write-Host "  ⚠️  STALE ISSUES ($($stale.Count) items, no update in $StaleDays+ days):" -ForegroundColor Red
        foreach ($issue in $stale) {
            $age = [math]::Round(((Get-Date) - [datetime]$issue.updatedAt).TotalDays)
            Write-Host "    #$($issue.number) — $($issue.title) (${age}d stale)" -ForegroundColor DarkRed
        }
    } else {
        Write-Host ""
        Write-Host "  ✅ No stale issues — all pipelines active" -ForegroundColor Green
    }

    # Open PRs
    $prs = Get-OpenPRs
    if ($prs.Count -gt 0) {
        Write-Host ""
        Write-Host "  📋 OPEN PRs ($($prs.Count)):" -ForegroundColor Cyan
        foreach ($pr in $prs) {
            Write-Host "    #$($pr.number) — $($pr.title) by $($pr.author.login)" -ForegroundColor DarkCyan
        }
    }

    # Weekly cadence
    $completed = Get-ContentCadence
    Write-Host ""
    Write-Host "  📊 WEEKLY CADENCE:" -ForegroundColor Magenta
    Write-Host "    Completed this week: $($completed.Count) items" -ForegroundColor White
    Write-Host "    Target: 2 videos + 3 articles + 1 newsletter = 6 items" -ForegroundColor DarkGray

    if ($completed.Count -lt 6) {
        $deficit = 6 - $completed.Count
        Write-Host "    ⚠️  Behind by $deficit items! Yo, we gotta cook more, man!" -ForegroundColor Red
    } else {
        Write-Host "    ✅ On track! The empire grows." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Yellow
}

# Main execution
Write-Report

if ($Loop) {
    Write-Host "  🔄 Looping every $IntervalMinutes minutes. Ctrl+C to stop." -ForegroundColor DarkGray
    while ($true) {
        Start-Sleep -Seconds ($IntervalMinutes * 60)
        Write-Report
    }
}
