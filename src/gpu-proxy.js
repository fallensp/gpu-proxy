/**
 * GPU Proxy for Vast.ai
 * 
 * This script serves as a proxy for interacting with Vast.ai's GPU resources
 * using their CLI commands.
 */

// Load environment variables from .env file
require('dotenv').config();

const { spawn, exec } = require('child_process');
const readline = require('readline');
const fs = require('fs');
const path = require('path');
const util = require('util');

const execPromise = util.promisify(exec);

class VastAIProxy {
  constructor(config = {}) {
    this.apiKey = config.apiKey || process.env.VAST_API_KEY;
    this.vastaiPath = config.vastaiPath || 'vastai';
    this.commandsCache = {};
    this.initialized = false;
  }

  /**
   * Initialize the proxy by checking if the vastai CLI is installed
   * and loading the commands reference
   */
  async initialize() {
    try {
      // Check if vastai CLI is installed
      await this.checkVastaiCli();
      
      // Load available commands from our documentation
      await this.loadCommands();
      
      this.initialized = true;
      console.log('VastAIProxy initialized successfully');
      return true;
    } catch (error) {
      console.error('Failed to initialize VastAIProxy:', error.message);
      return false;
    }
  }

  /**
   * Check if the vastai CLI is available
   */
  async checkVastaiCli() {
    try {
      const { stdout } = await execPromise(`${this.vastaiPath} --help`);
      console.log('Vastai CLI found:', stdout.includes('vastai'));
      return true;
    } catch (error) {
      console.error('Vastai CLI not found. Make sure it is installed and in your PATH.');
      console.error('You can install it with: pip install vastai');
      throw new Error('Vastai CLI not found');
    }
  }

  /**
   * Load the list of available commands from our documentation
   */
  async loadCommands() {
    try {
      const commandsFilePath = path.join(__dirname, '..', 'docs', 'vast-ai-cli-commands.txt');
      
      if (!fs.existsSync(commandsFilePath)) {
        console.warn('Commands reference file not found. Some features may not work correctly.');
        return;
      }

      const content = fs.readFileSync(commandsFilePath, 'utf-8');
      
      // Parse commands from the documentation
      const commandRegex = /(\w+(?:\s+\w+)*)\s+(.+?)(?=\n\s+\w+\s+|$)/gs;
      let match;
      
      while ((match = commandRegex.exec(content)) !== null) {
        const command = match[1].trim();
        const description = match[2].trim();
        
        if (command && !command.match(/^\d+$/) && command !== 'usage:' && !command.includes('positional arguments')) {
          this.commandsCache[command] = description;
        }
      }
      
      console.log(`Loaded ${Object.keys(this.commandsCache).length} commands`);
    } catch (error) {
      console.error('Error loading commands:', error.message);
    }
  }

  /**
   * Execute a vastai command
   * @param {Array} args - The command arguments
   * @param {Object} options - Options for execution
   * @returns {Promise<Object>} The command result
   */
  async executeCommand(args, options = {}) {
    if (!this.initialized) {
      await this.initialize();
    }

    return new Promise((resolve, reject) => {
      const command = `${this.vastaiPath} ${args.join(' ')}`;
      console.log(`Executing: ${command}`);
      
      // Set the API key if provided
      const env = { ...process.env };
      if (this.apiKey) {
        args.push('--api-key', this.apiKey);
      }
      
      const proc = spawn(this.vastaiPath, args, {
        env,
        shell: true,
        stdio: options.interactive ? 'inherit' : 'pipe'
      });
      
      if (options.interactive) {
        proc.on('close', (code) => {
          if (code === 0) {
            resolve({ success: true, code });
          } else {
            reject(new Error(`Command failed with code ${code}`));
          }
        });
        return;
      }
      
      let stdout = '';
      let stderr = '';
      
      proc.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      
      proc.on('close', (code) => {
        if (code === 0) {
          try {
            // Try to parse as JSON if the response looks like JSON
            if (stdout.trim().startsWith('{') || stdout.trim().startsWith('[')) {
              const result = JSON.parse(stdout);
              resolve({ success: true, data: result, raw: stdout });
            } else {
              resolve({ success: true, data: stdout, raw: stdout });
            }
          } catch (e) {
            resolve({ success: true, data: stdout, raw: stdout });
          }
        } else {
          reject(new Error(`Command failed with code ${code}: ${stderr}`));
        }
      });
      
      proc.on('error', (err) => {
        reject(new Error(`Failed to spawn process: ${err.message}`));
      });
    });
  }

  /**
   * List available instances
   */
  async listInstances(filters = {}) {
    const args = ['search', 'offers', '--raw'];
    
    // Add filters as arguments
    Object.entries(filters).forEach(([key, value]) => {
      args.push(`--${key}`, value);
    });
    
    return this.executeCommand(args);
  }

  /**
   * Get information about currently rented instances
   */
  async showInstances() {
    return this.executeCommand(['show', 'instances', '--raw']);
  }

  /**
   * Create a new instance
   */
  async createInstance(options = {}) {
    const args = ['create', 'instance'];
    
    Object.entries(options).forEach(([key, value]) => {
      args.push(`--${key}`, value);
    });
    
    return this.executeCommand(args);
  }

  /**
   * Destroy an instance
   */
  async destroyInstance(instanceId) {
    return this.executeCommand(['destroy', 'instance', instanceId]);
  }

  /**
   * SSH into an instance
   */
  async sshInstance(instanceId, sshCommand = '') {
    const args = ['ssh', instanceId];
    
    if (sshCommand) {
      args.push(sshCommand);
    }
    
    return this.executeCommand(args, { interactive: true });
  }

  /**
   * List all available commands
   */
  listCommands() {
    return Object.keys(this.commandsCache).map(cmd => ({
      command: cmd,
      description: this.commandsCache[cmd]
    }));
  }
  
  /**
   * Run any arbitrary vastai command
   */
  async runCommand(commandStr) {
    const args = commandStr.split(' ');
    return this.executeCommand(args);
  }
}

// Export the proxy class
module.exports = VastAIProxy;

// Example usage if script is run directly
if (require.main === module) {
  const readline = require('readline');
  const proxy = new VastAIProxy();
  
  // Create CLI interface
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  
  // Simple CLI
  const promptCommand = () => {
    rl.question('gpu-proxy> ', async (input) => {
      if (input.toLowerCase() === 'exit' || input.toLowerCase() === 'quit') {
        rl.close();
        return;
      }
      
      try {
        if (input.startsWith('!')) {
          // Direct vastai command
          const result = await proxy.runCommand(input.slice(1).trim());
          console.log(JSON.stringify(result, null, 2));
        } else if (input === 'list') {
          // List instances
          const instances = await proxy.listInstances();
          console.log(JSON.stringify(instances, null, 2));
        } else if (input === 'my-instances') {
          // Show my instances
          const instances = await proxy.showInstances();
          console.log(JSON.stringify(instances, null, 2));
        } else if (input === 'help') {
          // Show help
          console.log('Available commands:');
          console.log('  list                - List available instances');
          console.log('  my-instances        - Show your rented instances');
          console.log('  !<vastai command>   - Run a vastai command directly');
          console.log('  help                - Show this help message');
          console.log('  exit, quit          - Exit the program');
        } else {
          console.log('Unknown command. Type "help" for available commands.');
        }
      } catch (error) {
        console.error('Error:', error.message);
      }
      
      promptCommand();
    });
  };
  
  // Initialize and start the CLI
  proxy.initialize().then(() => {
    console.log('GPU Proxy CLI. Type "help" for available commands.');
    promptCommand();
  }).catch(error => {
    console.error('Failed to initialize:', error.message);
    process.exit(1);
  });
} 