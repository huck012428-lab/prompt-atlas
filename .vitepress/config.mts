import { defineConfig } from 'vitepress'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const DIRECTION_LABELS: Record<string, string> = {
  rag: 'RAG',
  agent: 'Agent',
  rlhf: 'RLHF',
  sft: 'SFT',
  multimodal: 'Multimodal',
  cot: 'Chain-of-Thought',
  eval: 'Evaluation',
}

const DIRECTION_ORDER = ['rag', 'agent', 'rlhf', 'sft', 'multimodal', 'cot', 'eval']

interface SidebarItem {
  text: string
  link?: string
  collapsed?: boolean
  items?: SidebarItem[]
}

function readCardTitle(filePath: string, fallback: string): string {
  try {
    const text = readFileSync(filePath, 'utf-8')
    const match = text.match(/^---\n([\s\S]*?)\n---/)
    if (!match) return fallback
    const titleMatch = match[1].match(/^title:\s*(.+)$/m)
    return titleMatch ? titleMatch[1].trim() : fallback
  } catch {
    return fallback
  }
}

function buildPromptsSidebar(): SidebarItem[] {
  const sidebar: SidebarItem[] = []
  for (const dir of DIRECTION_ORDER) {
    const dirPath = join('prompts', dir)
    let files: string[]
    try {
      files = readdirSync(dirPath).filter((f) => f.endsWith('.md')).sort()
    } catch {
      continue
    }
    if (files.length === 0) continue
    sidebar.push({
      text: `${DIRECTION_LABELS[dir]} (${files.length})`,
      collapsed: false,
      items: files.map((f) => {
        const slug = f.replace(/\.md$/, '')
        const title = readCardTitle(join(dirPath, f), slug)
        return {
          text: title,
          link: `/prompts/${dir}/${slug}`,
        }
      }),
    })
  }
  return sidebar
}

function buildDocsSidebar(): SidebarItem[] {
  return [
    {
      text: 'Getting started',
      collapsed: false,
      items: [
        { text: 'Quickstart', link: '/docs/QUICKSTART' },
        { text: 'Schema reference', link: '/docs/SCHEMA' },
        { text: 'Safety policy', link: '/docs/SAFETY' },
      ],
    },
    {
      text: 'Project',
      collapsed: false,
      items: [
        { text: 'Roadmap', link: '/docs/ROADMAP' },
        { text: 'Changelog', link: '/docs/CHANGELOG' },
        {
          text: 'Card template (raw)',
          link: 'https://github.com/huck012428-lab/prompt-atlas/blob/main/templates/prompt-card.md',
        },
      ],
    },
  ]
}

export default defineConfig({
  title: 'prompt-atlas',
  description:
    'Curated Prompt Card library for LLM trainers, AI PMs & evaluation teams · 面向 LLM trainer / AI PM / 模型评估团队的精选 Prompt 库',

  // GitHub Pages serves at https://huck012428-lab.github.io/prompt-atlas/
  base: '/prompt-atlas/',

  // Don't fail the build on dead links during the bootstrap phase.
  // Tighten this to false once the site is stable.
  ignoreDeadLinks: true,

  // Files VitePress should NOT process as pages.
  srcExclude: [
    'node_modules/**',
    '.github/**',
    '.vitepress/dist/**',
    '.vitepress/cache/**',
    'scripts/**',
    'docs/specs/**',
    'templates/**',
  ],

  cleanUrls: true,

  // INDEX.md is our auto-generated catalog. On macOS the case-insensitive
  // filesystem can confuse it with the implicit index.md home. Rewrite it
  // to a lowercased URL so README.md unambiguously serves at "/".
  rewrites: {
    'INDEX.md': 'catalog.md',
    'README.md': 'index.md',
  },

  // Our prompt content uses {{variable}} as placeholder syntax. Vue's default
  // template compiler treats {{ ... }} as interpolation, which breaks the
  // build. Swap Vue's interpolation delimiters to a sequence that does not
  // appear in the cards.
  vue: {
    template: {
      compilerOptions: {
        // Our prompt content uses {{variable}} as placeholder syntax. Vue's
        // default template compiler treats {{ ... }} as interpolation, which
        // breaks the build. Swap delimiters to a sequence that does not
        // appear in the cards.
        delimiters: ['<%=', '=%>'],
      },
    },
  },

  themeConfig: {
    nav: [
      { text: 'Quickstart', link: '/docs/QUICKSTART' },
      { text: 'Browse cards', link: '/prompts/rag/retrieval-relevance-evaluator' },
      { text: 'Catalog', link: '/catalog' },
      { text: 'Roadmap', link: '/docs/ROADMAP' },
    ],

    sidebar: {
      '/prompts/': buildPromptsSidebar(),
      '/docs/': buildDocsSidebar(),
    },

    search: {
      provider: 'local',
      options: {
        detailedView: true,
      },
    },

    outline: {
      level: [2, 3],
      label: 'On this page',
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/huck012428-lab/prompt-atlas' },
    ],

    editLink: {
      pattern: 'https://github.com/huck012428-lab/prompt-atlas/edit/main/:path',
      text: 'Edit this page on GitHub',
    },

    footer: {
      message:
        'Code MIT · Prompt content CC-BY-4.0. See <a href="https://github.com/huck012428-lab/prompt-atlas/blob/main/LICENSE">LICENSE</a>.',
      copyright: '© 2026 prompt-atlas contributors',
    },
  },

  markdown: {
    lineNumbers: false,
    theme: {
      light: 'github-light',
      dark: 'github-dark',
    },
  },

  // Sitemap generation for search-engine discovery.
  sitemap: {
    hostname: 'https://huck012428-lab.github.io/prompt-atlas/',
  },
})
