#!/usr/bin/env node
/*
 * ProjectIntel CLI
 *
 * This tool parses a PROJECT_INDEX.json file and exposes a number of commands
 * to explore and analyse the structure of a codebase.  It avoids external
 * dependencies to remain portable in environments without internet access.
 */

import { existsSync, readFileSync } from 'fs'
import { basename, dirname, resolve, sep } from 'path'
import * as readline from 'readline'

// Some consumers of this CLI (e.g. piping the output through `head` or
// other utilities) may close the stdout stream before all output is
// flushed.  In that case Node.js emits an EPIPE error.  We trap this
// specific error so the CLI exits cleanly without throwing.  See
// https://nodejs.org/api/process.html#signal-events for details.
process.stdout.on('error', err => {
  if (err.code === 'EPIPE') {
    // Silently ignore EPIPE which indicates the pipe on stdout was closed.
    return
  }
  throw err
})

/**
 * Parse .gitignore patterns and return exclusion patterns array
 */
function parseGitignore(projectRoot) {
  const gitignorePath = resolve(projectRoot, '.gitignore')
  const patterns = []

  // Always exclude these patterns by default
  const defaultExclusions = [
    'project-intel.mjs',
    'project-intel.js',
    '**/archive/**',
    '**/archived/**',
    '**/.archive/**',
    '**/.archived/**',
    'Archive*.zip',
    'archive.zip',
    'node_modules/**',
    '.next/**',
    '.git/**',
    'coverage/**',
    '.vercel/**',
    '*.tsbuildinfo',
    '.DS_Store',
    '*.backup',
    '*.bak',
    '*.old',
    '.backups/**',
  ]

  patterns.push(...defaultExclusions)

  // Read .gitignore if it exists
  if (existsSync(gitignorePath)) {
    try {
      const content = readFileSync(gitignorePath, 'utf8')
      const lines = content
        .split('\n')
        .map(line => line.trim())
        .filter(line => line && !line.startsWith('#'))
      patterns.push(...lines)
    } catch (_err) {
      // Ignore errors reading .gitignore
    }
  }

  return patterns
}

/**
 * Check if a file path matches any of the exclusion patterns
 */
function shouldExclude(filePath, patterns) {
  for (const pattern of patterns) {
    if (matchesPattern(filePath, pattern)) {
      return true
    }
  }
  return false
}

/**
 * Simple gitignore-style pattern matching
 */
function matchesPattern(filePath, pattern) {
  // Remove leading slash
  if (pattern.startsWith('/')) {
    pattern = pattern.substring(1)
  }

  // Directory pattern (ends with /)
  if (pattern.endsWith('/')) {
    const dirPattern = pattern.slice(0, -1)
    return (
      filePath.includes('/' + dirPattern + '/') ||
      filePath.startsWith(dirPattern + '/') ||
      filePath === dirPattern
    )
  }

  // Handle ** (match any directories)
  if (pattern.includes('**')) {
    const regexPattern = pattern
      .replace(/\*\*/g, '.*')
      .replace(/\*/g, '[^/]*')
      .replace(/\./g, '\\.')
    const regex = new RegExp('^' + regexPattern + '$')
    return regex.test(filePath)
  }

  // Handle * (match within segment)
  if (pattern.includes('*')) {
    const regexPattern = pattern.replace(/\*/g, '[^/]*').replace(/\./g, '\\.')
    const regex = new RegExp('^' + regexPattern + '$')
    return regex.test(filePath) || regex.test(basename(filePath))
  }

  // Exact match
  return (
    filePath === pattern ||
    filePath.endsWith('/' + pattern) ||
    basename(filePath) === pattern
  )
}

/**
 * Filter an array of file paths using exclusion patterns
 * @private - Currently unused but kept for potential future use
 */
function _filterFiles(files, patterns) {
  return files.filter(file => !shouldExclude(file, patterns))
}

/**
 * OutputBuffer class to collect and manage output with line limit warnings
 */
class OutputBuffer {
  constructor(command, lineLimit = 200) {
    this.lines = []
    this.command = command
    this.lineLimit = lineLimit
    this.forceOutput = false
  }

  setForce(force) {
    this.forceOutput = force
  }

  write(text) {
    const newLines = text.split('\n')
    // Handle cases where text doesn't end with newline
    if (this.lines.length > 0 && newLines.length > 0) {
      this.lines[this.lines.length - 1] += newLines[0]
      newLines.shift()
    }
    this.lines.push(...newLines)
  }

  getLineCount() {
    return this.lines.length
  }

  async flush() {
    const lineCount = this.getLineCount()

    // If under limit or force flag set, output immediately
    if (lineCount < this.lineLimit || this.forceOutput) {
      const output = this.lines.join('\n')
      process.stdout.write(output)
      return
    }

    // Check if running in interactive mode
    const isInteractive = process.stdin.isTTY && process.stdout.isTTY

    if (!isInteractive) {
      // Non-interactive: show warning to stderr and output anyway
      process.stderr.write(
        `\n⚠️  Warning: Output is ${lineCount} lines (limit: ${this.lineLimit})\n`
      )
      process.stderr.write(
        `   Consider using --force to suppress this warning\n\n`
      )
      const output = this.lines.join('\n')
      process.stdout.write(output)
      return
    }

    // Interactive mode: show warning and prompt
    const suggestion = this.getSuggestion()
    process.stderr.write(`\n⚠️  Large Output Warning\n`)
    process.stderr.write(
      `   This command will produce ${lineCount} lines of output (limit: ${this.lineLimit})\n\n`
    )
    if (suggestion) {
      process.stderr.write(`💡 Suggestion: ${suggestion}\n\n`)
    }
    process.stderr.write(`Options:\n`)
    process.stderr.write(`  [y] Show all output anyway\n`)
    process.stderr.write(`  [n] Cancel and refine your query\n`)
    process.stderr.write(`  [h] Show first 50 lines (head)\n`)
    process.stderr.write(`  Or use --force flag to skip this prompt\n\n`)

    const answer = await this.promptUser('Continue? [y/n/h]: ')

    switch (answer.toLowerCase()) {
      case 'y':
      case 'yes':
        const output = this.lines.join('\n')
        process.stdout.write(output)
        break
      case 'h':
      case 'head':
        const headOutput = this.lines.slice(0, 50).join('\n')
        process.stdout.write(headOutput + '\n')
        process.stderr.write(`\n... (${lineCount - 50} more lines omitted)\n`)
        break
      case 'n':
      case 'no':
      default:
        process.stderr.write('\nOutput cancelled. Try refining your query.\n')
        break
    }
  }

  async promptUser(question) {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stderr,
    })

    return new Promise(resolve => {
      rl.question(question, answer => {
        rl.close()
        resolve(answer.trim())
      })
    })
  }

  getSuggestion() {
    const suggestions = {
      tree: 'Use --max-depth <n> to limit tree depth, or focus on a specific directory',
      search:
        'Use -l <n> flag to limit results, or make your search term more specific',
      callers: 'Use -l <n> flag to limit the number of results shown',
      callees: 'Use -l <n> flag to limit the number of results shown',
      dead: 'Use -l <n> flag to limit the number of dead functions shown',
      importers: 'Use -l <n> flag to limit the number of importers shown',
      investigate:
        'Use -l <n> to limit results per term, or investigate fewer terms',
      sanitize: 'Use -l <n> to limit results, or remove --tests flag',
      docs: 'Use -l <n> to limit results, or be more specific with your search term',
      report: 'Use --focus <path> to analyze a specific directory',
    }
    return (
      suggestions[this.command] || 'Try using available flags to limit output'
    )
  }
}

// Cache loaded index and derived structures for performance
let cachedIndex = null
let cachedPath = null
let cachedDerived = null
let cachedExclusionPatterns = null

/**
 * Find the project root by searching for PROJECT_INDEX.json or project markers.
 * Walks up the directory tree from the current working directory.
 */
function findProjectRoot(startPath = process.cwd()) {
  let currentPath = startPath
  const root = resolve(sep) // Filesystem root

  while (currentPath !== root) {
    // Check for PROJECT_INDEX.json
    const indexPath = resolve(currentPath, 'PROJECT_INDEX.json')
    if (existsSync(indexPath)) {
      return currentPath
    }

    // Check for common project root markers
    const markers = ['package.json', '.git', 'pom.xml', 'Cargo.toml', 'go.mod']
    for (const marker of markers) {
      const markerPath = resolve(currentPath, marker)
      if (existsSync(markerPath)) {
        // Found a project marker, check if PROJECT_INDEX.json is here
        const indexAtMarker = resolve(currentPath, 'PROJECT_INDEX.json')
        if (existsSync(indexAtMarker)) {
          return currentPath
        }
      }
    }

    // Move up one directory
    const parentPath = dirname(currentPath)
    if (parentPath === currentPath) {
      // Reached the top, can't go further
      break
    }
    currentPath = parentPath
  }

  // Not found, return the starting path (will fail later with helpful error)
  return startPath
}

function loadIndex(indexPath) {
  let abs

  // If using default path, search for project root
  if (indexPath === 'PROJECT_INDEX.json') {
    const projectRoot = findProjectRoot()
    abs = resolve(projectRoot, indexPath)
  } else {
    // Custom path specified, use it as-is
    abs = resolve(process.cwd(), indexPath)
  }

  // Check if file exists
  if (!existsSync(abs)) {
    const error = new Error(
      `PROJECT_INDEX.json not found at: ${abs}\n\n` +
        `Please generate the index first. You can typically do this by:\n` +
        `  1. Running the /index slash command in Claude Code, or\n` +
        `  2. Running your project's index generation script\n\n` +
        `The index file should be in your project root directory.`
    )
    error.code = 'ENOENT'
    throw error
  }

  if (!cachedIndex || cachedPath !== abs) {
    try {
      const raw = readFileSync(abs, 'utf8')
      cachedIndex = JSON.parse(raw)
      cachedPath = abs
      cachedDerived = null
    } catch (parseError) {
      if (parseError instanceof SyntaxError) {
        const error = new Error(
          `Invalid JSON in ${abs}\n\n` +
            `The PROJECT_INDEX.json file appears to be corrupted or invalid.\n` +
            `Please regenerate it using /index or your index generation script.`
        )
        error.code = 'INVALID_JSON'
        throw error
      }
      throw parseError
    }
  }
  return cachedIndex
}

function buildDerived(data, exclusionPatterns = []) {
  if (cachedDerived && cachedExclusionPatterns === exclusionPatterns)
    return cachedDerived

  const fnToFiles = new Map()
  for (const [file, value] of Object.entries(data.f)) {
    // Skip excluded files
    if (exclusionPatterns.length && shouldExclude(file, exclusionPatterns)) {
      continue
    }

    const symbols = Array.isArray(value) && value.length > 1 ? value[1] : []
    if (Array.isArray(symbols)) {
      for (const sym of symbols) {
        const name = sym.split(':')[0]
        if (!fnToFiles.has(name)) fnToFiles.set(name, new Set())
        fnToFiles.get(name).add(file)
      }
    }
  }
  const callGraph = new Map()
  const reverseGraph = new Map()
  if (Array.isArray(data.g)) {
    for (const edge of data.g) {
      if (!Array.isArray(edge) || edge.length < 2) continue
      const src = edge[0]
      const tgt = edge[1]
      if (!callGraph.has(src)) callGraph.set(src, new Set())
      callGraph.get(src).add(tgt)
      if (!reverseGraph.has(tgt)) reverseGraph.set(tgt, new Set())
      reverseGraph.get(tgt).add(src)
    }
  }
  const fileImports = new Map()
  const moduleImporters = new Map()
  if (data.deps) {
    for (const [file, modules] of Object.entries(data.deps)) {
      // Skip excluded files
      if (exclusionPatterns.length && shouldExclude(file, exclusionPatterns)) {
        continue
      }

      if (!Array.isArray(modules)) continue
      fileImports.set(file, modules)
      for (const mod of modules) {
        if (!moduleImporters.has(mod)) moduleImporters.set(mod, new Set())
        moduleImporters.get(mod).add(file)
      }
    }
  }
  cachedDerived = {
    fnToFiles,
    callGraph,
    reverseGraph,
    fileImports,
    moduleImporters,
  }
  cachedExclusionPatterns = exclusionPatterns
  return cachedDerived
}

// Build directory tree from file paths
function buildDirTree(filePaths) {
  const root = { name: '.', children: new Map(), fileCount: 0 }
  for (const file of filePaths) {
    const parts = file.split('/')
    let node = root
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      if (!node.children.has(part)) {
        node.children.set(part, {
          name: part,
          children: new Map(),
          fileCount: 0,
        })
      }
      node = node.children.get(part)
      node.fileCount += 1
    }
  }
  return root
}

// Print directory tree using box‑drawing characters
function printDirTree(
  node,
  prefix = '',
  depthLimit,
  includeFiles = false,
  currentDepth = 0
) {
  const children = Array.from(node.children.values()).sort((a, b) =>
    a.name.localeCompare(b.name)
  )
  children.forEach((child, idx) => {
    const last = idx === children.length - 1
    const connector = last ? '└── ' : '├── '
    const isDir = child.children.size > 0
    if (isDir) {
      process.stdout.write(
        prefix +
          connector +
          child.name +
          '/ (' +
          child.fileCount +
          ' files)' +
          '\n'
      )
    } else if (includeFiles) {
      process.stdout.write(prefix + connector + child.name + '\n')
    }
    const newPrefix = prefix + (last ? '    ' : '│   ')
    const nextDepth = currentDepth + 1
    if ((depthLimit === undefined || nextDepth < depthLimit) && isDir) {
      printDirTree(child, newPrefix, depthLimit, includeFiles, nextDepth)
    }
  })
}

// Summarise file or directory
function summarisePath(data, derived, targetPath) {
  const allFiles = new Set(
    Object.keys(data.f).concat(Object.keys(data.d || {}))
  )
  const prefix = targetPath.endsWith('/') ? targetPath : targetPath + '/'
  if (allFiles.has(targetPath)) {
    // Summarise file
    const fileInfo = data.f[targetPath] || null
    const lang = fileInfo && fileInfo.length ? fileInfo[0] : 'unknown'
    const symbols =
      fileInfo && fileInfo.length > 1 && Array.isArray(fileInfo[1])
        ? fileInfo[1]
        : []
    const sigs = symbols.map(s => {
      const parts = s.split(':')
      return {
        name: parts[0],
        line: parts[1],
        signature: parts[2] || '',
        returnType: parts[3] || '',
        calls: parts[4] ? parts[4].split(',').filter(Boolean) : [],
      }
    })
    const imports = derived.fileImports.get(targetPath) || []
    let summary = ''
    summary += `File ${targetPath}\n`
    summary += `Language: ${lang}\n`
    if (imports.length) summary += `Imports: ${imports.join(', ')}\n`
    if (sigs.length) {
      summary += 'Exported symbols:\n'
      for (const sig of sigs) {
        summary += `  - ${sig.name} (line ${sig.line})`
        if (sig.signature) summary += `: (${sig.signature})`
        if (sig.returnType) summary += ` -> ${sig.returnType}`
        if (sig.calls && sig.calls.length)
          summary += ` [calls: ${sig.calls.join(', ')}]`
        summary += '\n'
      }
    }
    if (data.d && data.d[targetPath]) {
      summary += 'Documentation preview:\n'
      summary += data.d[targetPath].join('\n') + '\n'
    }
    return summary
  }
  // Summarise directory
  const categories = {
    pages: [],
    layouts: [],
    routes: [],
    components: [],
    tests: [],
    docs: [],
    others: [],
  }
  const prefixLen = prefix.length
  for (const file of allFiles) {
    if (!file.startsWith(prefix)) continue
    const rest = file.substring(prefixLen)
    if (rest.includes('/')) continue
    if (/page\.tsx$/i.test(file)) {
      categories.pages.push(file)
    } else if (/layout\.tsx$/i.test(file)) {
      categories.layouts.push(file)
    } else if (/route\.(ts|tsx)$/i.test(file)) {
      categories.routes.push(file)
    } else if (/__tests__|\.test\.|\.spec\./i.test(file)) {
      categories.tests.push(file)
    } else if (/\.md$/i.test(file)) {
      categories.docs.push(file)
    } else if (/components?\//i.test(targetPath) || /components/i.test(file)) {
      categories.components.push(file)
    } else {
      categories.others.push(file)
    }
  }
  let summary = `Directory ${targetPath}\n`
  function addCat(name, arr) {
    if (arr.length) {
      summary += `- ${name}: ${arr.length} file${arr.length > 1 ? 's' : ''}`
      const show = arr.slice(0, 3).map(f => f.split('/').pop())
      summary += ` (e.g. ${show.join(', ')})\n`
    }
  }
  addCat('pages', categories.pages)
  addCat('layouts', categories.layouts)
  addCat('routes', categories.routes)
  addCat('components', categories.components)
  addCat('tests', categories.tests)
  addCat('docs', categories.docs)
  addCat('other files', categories.others)
  return summary
}

// Find call path using BFS
function findCallPath(callGraph, start, target) {
  if (start === target) return [start]
  const queue = []
  const visited = new Set()
  queue.push([start])
  visited.add(start)
  while (queue.length) {
    const path = queue.shift()
    const node = path[path.length - 1]
    const neighbours = callGraph.get(node) || new Set()
    for (const neigh of neighbours) {
      if (visited.has(neigh)) continue
      const newPath = path.concat([neigh])
      if (neigh === target) return newPath
      visited.add(neigh)
      queue.push(newPath)
    }
  }
  return null
}

// Simple argument parser.  Returns { indexPath, command, args, opts }
function parseCommandLine(argv) {
  let indexPath = 'PROJECT_INDEX.json'
  const args = argv.slice(2)
  // extract global --index or -i
  let i = 0
  while (i < args.length) {
    const arg = args[i]
    if (arg === '--index' || arg === '-i') {
      indexPath = args[i + 1]
      args.splice(i, 2)
      continue
    }
    i++
  }
  const command = args.shift()
  return { indexPath, command, args }
}

// Parse options for a command.  Returns { opts, positional }
function parseOptions(args) {
  const opts = {}
  const positional = []
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    if (arg.startsWith('--')) {
      const key = arg.substring(2)
      const next = args[i + 1]
      if (next && !next.startsWith('-')) {
        opts[key] = next
        i++
      } else {
        opts[key] = true
      }
    } else if (arg.startsWith('-') && arg.length === 2) {
      const key = arg.substring(1)
      const next = args[i + 1]
      if (next && !next.startsWith('-')) {
        opts[key] = next
        i++
      } else {
        opts[key] = true
      }
    } else {
      positional.push(arg)
    }
  }
  return { opts, positional }
}

// Main dispatcher
async function main() {
  const { indexPath, command, args } = parseCommandLine(process.argv)

  // Show help if no command provided or help requested
  if (
    !command ||
    command === 'help' ||
    command === '--help' ||
    command === '-h'
  ) {
    printHelp()
    return
  }

  // Load index with error handling
  let data, derived, exclusionPatterns, projectRoot
  try {
    data = loadIndex(indexPath)
    // Find project root for exclusion patterns
    projectRoot = findProjectRoot()
    exclusionPatterns = parseGitignore(projectRoot)
    derived = buildDerived(data, exclusionPatterns)
  } catch (err) {
    console.error(`Error loading index from ${indexPath}:`)
    console.error(err.message)
    console.error(
      '\nRun without arguments or with --help to see usage information.'
    )
    process.exit(1)
  }

  // Helper to get filtered file list
  const getFilteredFiles = () => {
    return Object.keys(data.f).filter(
      file => !shouldExclude(file, exclusionPatterns)
    )
  }

  // Create output buffer for the command
  const buffer = new OutputBuffer(command)

  // Temporarily intercept stdout to collect output
  const originalWrite = process.stdout.write.bind(process.stdout)
  process.stdout.write = (chunk, encoding, callback) => {
    buffer.write(chunk.toString())
    if (callback) callback()
    return true
  }

  try {
    switch (command) {
      case 'stats': {
        const { opts } = parseOptions(args)
        const stats = data.stats || {}
        if (opts.json) {
          process.stdout.write(JSON.stringify(stats, null, 2) + '\n')
        } else {
          process.stdout.write('Total files: ' + stats.total_files + '\n')
          process.stdout.write(
            'Total directories: ' + stats.total_directories + '\n'
          )
          process.stdout.write('Fully parsed:\n')
          for (const [lang, count] of Object.entries(
            stats.fully_parsed || {}
          )) {
            process.stdout.write(`  - ${lang}: ${count} files\n`)
          }
          process.stdout.write('Listed only (unparsed):\n')
          for (const [ext, count] of Object.entries(stats.listed_only || {})) {
            process.stdout.write(`  - ${ext}: ${count} files\n`)
          }
          process.stdout.write(
            'Markdown files: ' + (stats.markdown_files || 0) + '\n'
          )
        }
        break
      }
      case 'tree': {
        const { opts } = parseOptions(args)
        const depthLimit = opts['max-depth']
          ? parseInt(opts['max-depth'], 10)
          : undefined
        const includeFiles = opts.files || false
        const filteredFiles = getFilteredFiles()
        const filteredDocs = Object.keys(data.d || {}).filter(
          doc => !shouldExclude(doc, exclusionPatterns)
        )
        const allFiles = new Set(filteredFiles.concat(filteredDocs))
        const tree = buildDirTree(Array.from(allFiles))
        printDirTree(tree, '', depthLimit, includeFiles)
        break
      }
      case 'search': {
        const term = args.shift()
        const { opts } = parseOptions(args)
        if (!term) {
          console.error('search requires a term')
          return
        }
        const limit = opts.l ? parseInt(opts.l, 10) : 20
        const regex = opts.regex
          ? new RegExp(term)
          : new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i')
        const results = []
        // search files (filtered)
        for (const file of getFilteredFiles()) {
          if (regex.test(file)) {
            results.push({ type: 'file', file })
            if (results.length >= limit) break
          }
        }
        if (results.length < limit) {
          for (const [fn, files] of derived.fnToFiles.entries()) {
            if (regex.test(fn)) {
              results.push({
                type: 'symbol',
                name: fn,
                files: Array.from(files),
              })
              if (results.length >= limit) break
            }
          }
        }
        if (opts.json) {
          process.stdout.write(JSON.stringify(results, null, 2) + '\n')
        } else {
          if (!results.length) {
            process.stdout.write('No matches found.\n')
          } else {
            for (const res of results) {
              if (res.type === 'file') {
                process.stdout.write(`File: ${res.file}\n`)
              } else {
                process.stdout.write(
                  `Symbol: ${res.name} (defined in ${res.files.join(', ')})\n`
                )
              }
            }
          }
        }
        break
      }
      case 'callers': {
        const fnName = args.shift()
        const { opts } = parseOptions(args)
        if (!fnName) {
          console.error('callers requires a function name')
          return
        }
        const limit = opts.l ? parseInt(opts.l, 10) : 20
        const callers = derived.reverseGraph.get(fnName)
          ? Array.from(derived.reverseGraph.get(fnName))
          : []
        const results = callers.slice(0, limit).map(caller => {
          return {
            caller,
            files: Array.from(derived.fnToFiles.get(caller) || []),
          }
        })
        if (opts.json) {
          process.stdout.write(JSON.stringify(results, null, 2) + '\n')
        } else {
          if (!results.length) {
            process.stdout.write(`No functions call ${fnName}.\n`)
          } else {
            for (const { caller, files } of results) {
              process.stdout.write(`${caller} (in ${files.join(', ')})\n`)
            }
          }
        }
        break
      }
      case 'callees': {
        const fnName = args.shift()
        const { opts } = parseOptions(args)
        if (!fnName) {
          console.error('callees requires a function name')
          return
        }
        const limit = opts.l ? parseInt(opts.l, 10) : 20
        const callees = derived.callGraph.get(fnName)
          ? Array.from(derived.callGraph.get(fnName))
          : []
        const results = callees.slice(0, limit).map(callee => {
          return {
            callee,
            files: Array.from(derived.fnToFiles.get(callee) || []),
          }
        })
        if (opts.json) {
          process.stdout.write(JSON.stringify(results, null, 2) + '\n')
        } else {
          if (!results.length) {
            process.stdout.write(
              `${fnName} does not call any functions in the index.\n`
            )
          } else {
            for (const { callee, files } of results) {
              process.stdout.write(
                `${fnName} calls ${callee} (defined in ${files.join(', ')})\n`
              )
            }
          }
        }
        break
      }
      case 'trace': {
        const start = args.shift()
        const target = args.shift()
        const { opts } = parseOptions(args)
        if (!start || !target) {
          console.error('trace requires two function names')
          return
        }
        const path = findCallPath(derived.callGraph, start, target)
        if (opts.json) {
          process.stdout.write(JSON.stringify({ path }, null, 2) + '\n')
        } else {
          if (!path) {
            process.stdout.write(`No call path from ${start} to ${target}.\n`)
          } else {
            process.stdout.write(path.join(' -> ') + '\n')
          }
        }
        break
      }
      case 'dead': {
        const { opts } = parseOptions(args)
        const limit = opts.l ? parseInt(opts.l, 10) : 50
        const list = []
        for (const fn of derived.fnToFiles.keys()) {
          if (!derived.reverseGraph.has(fn)) {
            list.push({
              name: fn,
              files: Array.from(derived.fnToFiles.get(fn) || []),
            })
            if (list.length >= limit) break
          }
        }
        if (opts.json) {
          process.stdout.write(JSON.stringify(list, null, 2) + '\n')
        } else {
          if (!list.length) {
            process.stdout.write('No dead functions detected.\n')
          } else {
            for (const item of list) {
              process.stdout.write(
                `${item.name} (defined in ${item.files.join(', ')})\n`
              )
            }
          }
        }
        break
      }
      case 'imports': {
        const file = args.shift()
        const { opts } = parseOptions(args)
        if (!file) {
          console.error('imports requires a file path')
          return
        }
        const imports = derived.fileImports.get(file) || []
        if (opts.json) {
          process.stdout.write(JSON.stringify(imports, null, 2) + '\n')
        } else {
          if (!imports.length) {
            process.stdout.write(
              `${file} does not import any modules recorded in the index.\n`
            )
          } else {
            process.stdout.write(`Imports for ${file}:\n`)
            for (const mod of imports) {
              process.stdout.write(`  - ${mod}\n`)
            }
          }
        }
        break
      }
      case 'importers': {
        const modName = args.shift()
        const { opts } = parseOptions(args)
        if (!modName) {
          console.error('importers requires a module specifier')
          return
        }
        const limit = opts.l ? parseInt(opts.l, 10) : 50
        const files = derived.moduleImporters.get(modName)
          ? Array.from(derived.moduleImporters.get(modName))
          : []
        const limited = files.slice(0, limit)
        if (opts.json) {
          process.stdout.write(JSON.stringify(limited, null, 2) + '\n')
        } else {
          if (!limited.length) {
            process.stdout.write(`No files import module ${modName}.\n`)
          } else {
            process.stdout.write(`Files that import ${modName}:\n`)
            for (const f of limited) {
              process.stdout.write(`  - ${f}\n`)
            }
          }
        }
        break
      }
      case 'metrics': {
        const { opts } = parseOptions(args)
        const inbound = []
        for (const [fn, callers] of derived.reverseGraph.entries()) {
          inbound.push({ fn, count: callers.size })
        }
        inbound.sort((a, b) => b.count - a.count)
        const outbound = []
        for (const [fn, callees] of derived.callGraph.entries()) {
          outbound.push({ fn, count: callees.size })
        }
        outbound.sort((a, b) => b.count - a.count)
        if (opts.json) {
          process.stdout.write(
            JSON.stringify(
              {
                topInbound: inbound.slice(0, 10),
                topOutbound: outbound.slice(0, 10),
              },
              null,
              2
            ) + '\n'
          )
        } else {
          process.stdout.write(
            'Top functions by number of callers (inbound edges):\n'
          )
          inbound.slice(0, 10).forEach(item => {
            process.stdout.write(`  - ${item.fn}: ${item.count}\n`)
          })
          process.stdout.write(
            '\nTop functions by number of callees (outbound edges):\n'
          )
          outbound.slice(0, 10).forEach(item => {
            process.stdout.write(`  - ${item.fn}: ${item.count}\n`)
          })
        }
        break
      }
      case 'summarize': {
        const target = args.shift()
        const { opts } = parseOptions(args)
        if (!target) {
          console.error('summarize requires a path')
          return
        }
        const summary = summarisePath(data, derived, target)
        if (opts.json) {
          process.stdout.write(JSON.stringify({ summary }, null, 2) + '\n')
        } else {
          process.stdout.write(summary)
        }
        break
      }
      case 'investigate': {
        /**
         * Investigate one or more search terms. This command performs a high‑level
         * analysis for each supplied term by searching file names, exported
         * symbols and documentation previews for matches. For each match it
         * provides a summary of the file, symbol and documentation contexts. The
         * goal of this command is to supply subagents with enough starting
         * context to orchestrate further exploration.
         *
         * Usage: investigate <term1> [term2 ...] [options]
         * Options:
         *   -l <n>       Limit results per term (default: 5)
         *   --json       Emit JSON output
         *
         */
        const { opts, positional } = parseOptions(args)
        const terms = positional.length ? positional : []
        const limit = opts.l ? parseInt(opts.l, 10) : 5
        if (!terms.length) {
          console.error('investigate requires at least one search term')
          return
        }
        const results = []
        for (const term of terms) {
          const regex = new RegExp(
            term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
            'i'
          )
          const termResult = { term, files: [], symbols: [], docs: [] }
          // File matches (filtered)
          for (const file of getFilteredFiles()) {
            if (regex.test(file)) {
              const summary = summarisePath(data, derived, file)
              termResult.files.push({ file, summary })
              if (termResult.files.length >= limit) break
            }
          }
          // Symbol matches
          if (termResult.symbols.length < limit) {
            for (const [fnName, files] of derived.fnToFiles.entries()) {
              if (regex.test(fnName)) {
                const callers = derived.reverseGraph.get(fnName)
                  ? Array.from(derived.reverseGraph.get(fnName))
                  : []
                const callees = derived.callGraph.get(fnName)
                  ? Array.from(derived.callGraph.get(fnName))
                  : []
                termResult.symbols.push({
                  name: fnName,
                  files: Array.from(files),
                  callers: callers.length,
                  callees: callees.length,
                })
                if (termResult.symbols.length >= limit) break
              }
            }
          }
          // Documentation matches
          if (data.d) {
            const docFiles = Object.keys(data.d)
            for (const doc of docFiles) {
              const content = (data.d[doc] || []).join('\n')
              if (regex.test(doc) || regex.test(content)) {
                termResult.docs.push({
                  file: doc,
                  preview: (data.d[doc] || []).join('\n'),
                })
                if (termResult.docs.length >= limit) break
              }
            }
          }
          results.push(termResult)
        }
        if (opts.json) {
          process.stdout.write(JSON.stringify(results, null, 2) + '\n')
        } else {
          for (const res of results) {
            process.stdout.write(`Investigate term: ${res.term}\n`)
            if (res.files.length) {
              process.stdout.write('  Files:\n')
              for (const f of res.files) {
                process.stdout.write(`    - ${f.file}\n`)
              }
            }
            if (res.symbols.length) {
              process.stdout.write('  Symbols:\n')
              for (const s of res.symbols) {
                process.stdout.write(
                  `    - ${s.name} (in ${s.files.join(', ')}, callers: ${s.callers}, callees: ${s.callees})\n`
                )
              }
            }
            if (res.docs.length) {
              process.stdout.write('  Documentation:\n')
              for (const d of res.docs) {
                process.stdout.write(`    - ${d.file}\n`)
              }
            }
            process.stdout.write('\n')
          }
        }
        break
      }
      case 'debug': {
        /**
         * Debug a file or function. When given a function name, this command
         * outputs its callers, callees and summary of the files where it is
         * defined. When given a file path, it summarises the file and lists
         * functions defined in it along with their callers and callees. This
         * assists agents in isolating issues within a flow (e.g. PDF generation).
         *
         * Usage: debug <fn|file> [options]
         * Options:
         *   --json     Emit JSON output
         */
        const target = args.shift()
        const { opts } = parseOptions(args)
        if (!target) {
          console.error('debug requires a function name or file path')
          return
        }
        let output = {}
        if (data.f[target] || (data.d && data.d[target])) {
          // Target is a file
          const summary = summarisePath(data, derived, target)
          const symbols = []
          const fileInfo = data.f[target] || null
          if (fileInfo && fileInfo.length > 1 && Array.isArray(fileInfo[1])) {
            for (const s of fileInfo[1]) {
              const name = s.split(':')[0]
              const callers = derived.reverseGraph.get(name)
                ? Array.from(derived.reverseGraph.get(name))
                : []
              const callees = derived.callGraph.get(name)
                ? Array.from(derived.callGraph.get(name))
                : []
              symbols.push({ name, callers, callees })
            }
          }
          output = {
            type: 'file',
            file: target,
            summary,
            symbols,
            imports: derived.fileImports.get(target) || [],
          }
          if (opts.json) {
            process.stdout.write(JSON.stringify(output, null, 2) + '\n')
          } else {
            process.stdout.write(output.summary)
            if (output.imports.length) {
              process.stdout.write('Imports:\n')
              for (const mod of output.imports) {
                process.stdout.write(`  - ${mod}\n`)
              }
            }
            if (symbols.length) {
              process.stdout.write('Defined symbols:\n')
              for (const s of symbols) {
                process.stdout.write(`  - ${s.name}\n`)
                if (s.callers.length)
                  process.stdout.write(
                    `      callers: ${s.callers.join(', ')}\n`
                  )
                if (s.callees.length)
                  process.stdout.write(
                    `      callees: ${s.callees.join(', ')}\n`
                  )
              }
            }
          }
        } else {
          // Assume target is a function name
          const fnName = target
          const files = derived.fnToFiles.get(fnName)
            ? Array.from(derived.fnToFiles.get(fnName))
            : []
          const callers = derived.reverseGraph.get(fnName)
            ? Array.from(derived.reverseGraph.get(fnName))
            : []
          const callees = derived.callGraph.get(fnName)
            ? Array.from(derived.callGraph.get(fnName))
            : []
          output = { type: 'symbol', name: fnName, files, callers, callees }
          if (opts.json) {
            process.stdout.write(JSON.stringify(output, null, 2) + '\n')
          } else {
            process.stdout.write(`Function ${fnName}\n`)
            if (files.length)
              process.stdout.write('Defined in: ' + files.join(', ') + '\n')
            if (callers.length)
              process.stdout.write('Callers: ' + callers.join(', ') + '\n')
            if (callees.length)
              process.stdout.write('Callees: ' + callees.join(', ') + '\n')
          }
        }
        break
      }
      case 'sanitize': {
        /**
         * Identify unused code and test files. By default, this command lists
         * exported functions with no callers (dead code). With the --tests flag
         * it additionally lists test files (files whose name matches common test
         * patterns) so that agents can decide whether they are still relevant.
         *
         * Usage: sanitize [options]
         * Options:
         *   -l <n>       Limit dead code entries (default: 50)
         *   --tests      Include test file listing
         *   --json       Emit JSON output
         */
        const { opts } = parseOptions(args)
        const limit = opts.l ? parseInt(opts.l, 10) : 50
        const deadList = []
        for (const fn of derived.fnToFiles.keys()) {
          if (!derived.reverseGraph.has(fn)) {
            deadList.push({
              name: fn,
              files: Array.from(derived.fnToFiles.get(fn) || []),
            })
            if (deadList.length >= limit) break
          }
        }
        let tests = []
        if (opts.tests) {
          for (const file of getFilteredFiles()) {
            if (/__tests__|\.test\.|\.spec\./i.test(file)) {
              tests.push(file)
            }
          }
        }
        if (opts.json) {
          process.stdout.write(
            JSON.stringify({ dead: deadList, tests }, null, 2) + '\n'
          )
        } else {
          process.stdout.write('Unused exported functions:\n')
          for (const item of deadList) {
            process.stdout.write(
              `  - ${item.name} (in ${item.files.join(', ')})\n`
            )
          }
          if (opts.tests) {
            process.stdout.write('\nTest files:\n')
            for (const f of tests) {
              process.stdout.write(`  - ${f}\n`)
            }
          }
        }
        break
      }
      case 'docs': {
        /**
         * Search and display documentation files. This command searches for
         * Markdown files and specification documents that match a term or, if
         * given a file path, displays a preview of that file. It helps agents
         * retrieve documentation relevant to a feature and compare it against
         * implementation.
         *
         * Usage: docs <term|file> [options]
         * Options:
         *   -l <n>       Limit results (default: 10)
         *   --json       Emit JSON output
         */
        const target = args.shift()
        const { opts } = parseOptions(args)
        const limit = opts.l ? parseInt(opts.l, 10) : 10
        if (!target) {
          console.error('docs requires a term or file path')
          return
        }
        // If target looks like a file path and exists in docs, show preview
        if (data.d && data.d[target]) {
          const preview = (data.d[target] || []).join('\n')
          const out = { file: target, preview }
          if (opts.json) {
            process.stdout.write(JSON.stringify(out, null, 2) + '\n')
          } else {
            process.stdout.write(`Documentation for ${target}:\n${preview}\n`)
          }
        } else {
          // search docs by term
          const regex = new RegExp(
            target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
            'i'
          )
          const matches = []
          if (data.d) {
            for (const doc of Object.keys(data.d)) {
              const content = (data.d[doc] || []).join('\n')
              if (regex.test(doc) || regex.test(content)) {
                matches.push({ file: doc, preview: content })
                if (matches.length >= limit) break
              }
            }
          }
          if (opts.json) {
            process.stdout.write(JSON.stringify(matches, null, 2) + '\n')
          } else {
            if (!matches.length) {
              process.stdout.write('No matching documentation found.\n')
            } else {
              process.stdout.write('Matching documentation files:\n')
              for (const m of matches) {
                process.stdout.write(`  - ${m.file}\n`)
              }
            }
          }
        }
        break
      }
      case 'report': {
        /**
         * Generate a comprehensive report of the repository or a subset. This
         * command aggregates statistics, highlights hotspots (functions with
         * many callers/callees), lists the most imported modules and shows
         * documentation counts. A --focus option can restrict analysis to
         * a particular directory prefix.
         *
         * Usage: report [--focus <path>] [options]
         * Options:
         *   --json       Emit JSON output
         */
        const { opts, positional: _positional } = parseOptions(args)
        const focus = opts.focus
        const files = []
        // Filter files by focus if provided (already filtered by exclusion patterns)
        for (const file of getFilteredFiles()) {
          if (!focus || file.startsWith(focus)) {
            files.push(file)
          }
        }
        // Stats
        const stats = {
          totalFiles: files.length,
          languages: {},
          docs: 0,
          tests: 0,
        }
        for (const file of files) {
          const info = data.f[file] || null
          const lang = info && info.length ? info[0] : 'unknown'
          stats.languages[lang] = (stats.languages[lang] || 0) + 1
          if (/__tests__|\.test\.|\.spec\./i.test(file)) stats.tests++
          if (/\.md$/i.test(file)) stats.docs++
        }
        // Hotspots
        const inboundCounts = []
        const outboundCounts = []
        for (const [fn, callers] of derived.reverseGraph.entries()) {
          inboundCounts.push({ fn, count: callers.size })
        }
        inboundCounts.sort((a, b) => b.count - a.count)
        for (const [fn, callees] of derived.callGraph.entries()) {
          outboundCounts.push({ fn, count: callees.size })
        }
        outboundCounts.sort((a, b) => b.count - a.count)
        // Module import counts
        const moduleCounts = []
        for (const [mod, importers] of derived.moduleImporters.entries()) {
          moduleCounts.push({ module: mod, count: importers.size })
        }
        moduleCounts.sort((a, b) => b.count - a.count)
        const report = {
          stats,
          topInbound: inboundCounts.slice(0, 10),
          topOutbound: outboundCounts.slice(0, 10),
          topModules: moduleCounts.slice(0, 10),
        }
        if (opts.json) {
          process.stdout.write(JSON.stringify(report, null, 2) + '\n')
        } else {
          process.stdout.write('Report\n')
          process.stdout.write(
            `Total files${focus ? ' in ' + focus : ''}: ${stats.totalFiles}\n`
          )
          process.stdout.write('Languages:\n')
          for (const [lang, count] of Object.entries(stats.languages)) {
            process.stdout.write(`  - ${lang}: ${count}\n`)
          }
          process.stdout.write(`Documentation files: ${stats.docs}\n`)
          process.stdout.write(`Test files: ${stats.tests}\n\n`)
          process.stdout.write(
            'Top functions by number of callers (inbound edges):\n'
          )
          for (const item of report.topInbound) {
            process.stdout.write(`  - ${item.fn}: ${item.count}\n`)
          }
          process.stdout.write(
            '\nTop functions by number of callees (outbound edges):\n'
          )
          for (const item of report.topOutbound) {
            process.stdout.write(`  - ${item.fn}: ${item.count}\n`)
          }
          process.stdout.write('\nTop imported modules:\n')
          for (const item of report.topModules) {
            process.stdout.write(`  - ${item.module}: ${item.count}\n`)
          }
        }
        break
      }
      default:
        console.error(`Unknown command: ${command}`)
        printHelp()
        break
    }
  } finally {
    // Restore original stdout
    process.stdout.write = originalWrite
  }

  // Check for --force and --json flags
  const { opts } = parseOptions(args)
  if (opts.force) {
    buffer.setForce(true)
  }

  // Skip buffering for JSON output, otherwise flush with prompts
  if (!opts.json) {
    await buffer.flush()
  } else {
    // For JSON output, write directly without buffering
    const output = buffer.lines.join('\n')
    process.stdout.write(output)
  }
}

function printHelp() {
  const help =
    `ProjectIntel CLI\n\n` +
    `Usage: project-intel [--index <file>] <command> [options]\n\n` +
    `Commands:\n` +
    `  stats                Show summary statistics\n` +
    `  tree                 Print the directory tree (options: --max-depth <n>, --files)\n` +
    `  search <term>        Search for files or symbols (options: --regex, -l <n>, --json)\n` +
    `  callers <fn>         List functions that call <fn> (options: -l <n>, --json)\n` +
    `  callees <fn>         List functions called by <fn> (options: -l <n>, --json)\n` +
    `  trace <fn1> <fn2>    Find a call path from fn1 to fn2 (options: --json)\n` +
    `  dead                 List exported functions never called (options: -l <n>, --json)\n` +
    `  imports <file>       List modules imported by <file> (options: --json)\n` +
    `  importers <module>   List files that import <module> (options: -l <n>, --json)\n` +
    `  metrics              Show functions with many callers/callees (options: --json)\n` +
    `  summarize <path>     Summarise a file or directory (options: --json)\n` +
    `  investigate <term...> Explore one or more terms across files, symbols and docs (options: -l <n>, --json)\n` +
    `  debug <fn|file>      Debug a function or file, showing callers, callees and summary (options: --json)\n` +
    `  sanitize             List unused functions and optionally test files (options: -l <n>, --tests, --json)\n` +
    `  docs <term|file>     Search documentation or preview a doc file (options: -l <n>, --json)\n` +
    `  report               Generate a repository report (options: --focus <path>, --json)\n\n` +
    `Global options:\n` +
    `  -i, --index <file>   Path to PROJECT_INDEX.json (default: PROJECT_INDEX.json)\n` +
    `  --force              Skip the 200-line output warning and show all output\n` +
    `  --json               Format output as JSON (also bypasses output limit)\n`
  process.stdout.write(help)
}

main()
