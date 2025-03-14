const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

/**
 * Crawls the Vast.ai API documentation and saves it locally
 */
async function crawlVastDocs() {
  console.log('Starting to crawl Vast.ai API documentation...');
  
  // Launch the browser with more options
  const browser = await puppeteer.launch({ 
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security']
  });
  
  const page = await browser.newPage();
  
  try {
    // Set a longer default timeout
    page.setDefaultTimeout(30000);
    
    // Configure the page
    await page.setViewport({ width: 1280, height: 800 });
    
    // Navigate to the Vast.ai API commands documentation
    const url = 'https://docs.vast.ai/api/commands';
    console.log(`Navigating to ${url}...`);
    
    // Set user agent to avoid blocking
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    
    // Navigate with longer timeout
    const response = await page.goto(url, { 
      waitUntil: 'networkidle2',
      timeout: 30000 
    });
    
    if (!response.ok()) {
      console.log(`HTTP status: ${response.status()}`);
    }
    
    // Create output directory if it doesn't exist
    const outputDir = path.join(__dirname, '..', 'docs');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    // Take a screenshot to see what's being loaded
    console.log('Taking screenshot of the page...');
    await page.screenshot({ 
      path: path.join(outputDir, 'page-screenshot.png'),
      fullPage: true 
    });
    
    // Wait a bit to ensure dynamic content loads
    console.log('Waiting for page to fully render...');
    // Use setTimeout instead of waitForTimeout which may not be available in some Puppeteer versions
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Get page title
    const title = await page.title();
    console.log(`Page title: ${title}`);
    
    // Save the entire HTML
    console.log('Saving full page HTML...');
    const fullHtml = await page.content();
    fs.writeFileSync(path.join(outputDir, 'full-page.html'), fullHtml);
    
    // Extract visible text from the page
    console.log('Extracting text content...');
    const textContent = await page.evaluate(() => {
      return document.body.innerText;
    });
    
    // Save the text content
    const textFilePath = path.join(outputDir, 'vast-ai-commands.txt');
    fs.writeFileSync(textFilePath, textContent);
    console.log(`Text content saved to ${textFilePath}`);
    
    // Attempt to find code blocks with vast commands
    console.log('Looking for CLI commands...');
    const cliCommands = await page.evaluate(() => {
      // Try various ways to identify code blocks
      const possibleCodeElements = [
        ...Array.from(document.querySelectorAll('pre')),
        ...Array.from(document.querySelectorAll('code')),
        ...Array.from(document.querySelectorAll('[class*="code"]')),
        ...Array.from(document.querySelectorAll('[class*="Code"]')),
        ...Array.from(document.querySelectorAll('[class*="syntax"]')),
        ...Array.from(document.querySelectorAll('[class*="Syntax"]'))
      ];
      
      // Extract text from these elements
      const textBlocks = possibleCodeElements.map(el => el.textContent.trim());
      
      // Filter for those containing 'vast'
      return textBlocks.filter(text => text.includes('vast')).join('\n\n===\n\n');
    });
    
    // Save CLI commands
    const commandsFilePath = path.join(outputDir, 'vast-ai-cli-commands.txt');
    if (cliCommands && cliCommands.length > 0) {
      fs.writeFileSync(commandsFilePath, cliCommands);
      console.log(`CLI commands saved to ${commandsFilePath}`);
    } else {
      // If no commands found directly, try alternative approach - look for text patterns
      console.log('No CLI commands found via DOM elements, trying text pattern matching...');
      
      // Look for command patterns in the text content
      const commandLines = textContent.split('\n')
        .filter(line => line.trim().startsWith('vast '))
        .join('\n\n');
      
      if (commandLines && commandLines.length > 0) {
        fs.writeFileSync(commandsFilePath, commandLines);
        console.log(`CLI commands (from text pattern) saved to ${commandsFilePath}`);
      } else {
        fs.writeFileSync(commandsFilePath, 'No CLI commands found');
        console.log('No CLI commands could be extracted');
      }
    }
    
    // Also try using the Fetch API directly to get the raw HTML
    console.log('Attempting direct fetch of URL...');
    const fetchResult = await page.evaluate(async (url) => {
      try {
        const response = await fetch(url);
        const text = await response.text();
        return { success: true, content: text };
      } catch (error) {
        return { success: false, error: error.toString() };
      }
    }, url);
    
    if (fetchResult.success) {
      fs.writeFileSync(path.join(outputDir, 'fetch-result.html'), fetchResult.content);
      console.log('Saved direct fetch result');
    } else {
      console.log('Direct fetch failed:', fetchResult.error);
    }
    
  } catch (error) {
    console.error('Error during crawling:', error);
  } finally {
    // Close the browser
    await browser.close();
    console.log('Crawling completed');
  }
}

// Run the crawler
crawlVastDocs(); 