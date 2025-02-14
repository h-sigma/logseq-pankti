import "@logseq/libs";
import {
  BlockCommandCallback,
  UIOptions,
} from "@logseq/libs/dist/LSPlugin.user";

interface GurbaniMatch {
  punjabi: string;
  translit: string;
  attributes: string;
  shabdID: string;
}

const closeUI = () => {
  logseq.provideUI({
    key: "gurbani-search-dialog",
    template: "",
  });
};

const dataStringify = (obj: any) => {
  return JSON.stringify(obj).replace(/"/g, "&quot;");
};

const insertIcon = (pankti: GurbaniMatch, uuid: string) => {
  return `
    <div style="position: absolute; top: 10px; right: 10px; cursor: pointer;"
        data-on-click="selectPankti" data-uuid="${uuid}" data-pankti="${dataStringify(pankti)}">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="5" x2="12" y2="19"></line>
        <line x1="5" y1="12" x2="19" y2="12"></line>
      </svg>
    </div>
  `;
};

const dsl = (matches: GurbaniMatch[], uuid: string) => {
  const results = dataStringify(matches);
  return `
    <div id="pankti-search" >
      <div class="results-container">
        ${
          matches.length === 0
            ? "<div>No matches found</div>"
            : matches
                .map(
                  (match, idx) => `
          <div class="match-item" style="margin: 10px 0; padding: 10px; border: 1px solid var(--ls-border-color); position: relative;">
            <div style="cursor: pointer;">
              <div style="font-weight: bold; margin-right: 40px;">${match.punjabi}</div>
              <div style="color: var(--ls-secondary-text-color);">${
                match.translit
              }</div>
              <div style="color: var(--ls-secondary-text-color);">${
                match.attributes
              }</div>
            </div>
            ${insertIcon(match, uuid)}
            <div style="position: absolute; top: 10px; right: 35px; cursor: pointer;"
                data-on-click="viewShabad" data-shabad-id="${
                  match.shabdID
                }" data-results="${results}">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
              </svg>
            </div>
          </div>
        `
                )
                .join("")
        }
      </div>
    </div>
  `;
};

const shabadDsl = (matches: GurbaniMatch[], results: GurbaniMatch[], uuid: string) => {
  return `
    <div id="pankti-search">
      <div style="padding: 20px;">
        <div style="display: flex; align-items: center; margin-bottom: 20px; gap: 20px;">
          <div style="cursor: pointer;" data-on-click="backToSearch" data-results="${dataStringify(
            results
          )}">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
          </div>
          <button style="cursor: pointer; padding: 4px 12px; border-radius: 4px; border: 1px solid var(--ls-border-color); background: var(--ls-primary-background-color); color: var(--ls-primary-text-color);"
            data-on-click="insertShabad" data-matches="${dataStringify(matches)}" data-uuid="${uuid}">
            Insert Shabad
          </button>
        </div>
        <div class="shabad-container">
          ${matches
            .map(
              (line) => `
            <div class="shabad-line" style="margin: 10px 0; padding: 10px; border: 1px solid var(--ls-border-color); position: relative;">
              <div style="font-weight: bold; margin-right: 40px;">${line.punjabi}</div>
              <div style="color: var(--ls-secondary-text-color);">${line.translit}</div>
              <div style="color: var(--ls-secondary-text-color); font-size: 0.9em;">${line.attributes}</div>
              ${insertIcon(line, uuid)}
            </div>
          `
            )
            .join("")}
        </div>
      </div>
    </div>
  `;
};

async function searchDatabase(
  text: string,
  searchType?: string
): Promise<GurbaniMatch[]> {
  console.log("Searching database...", searchType, text);
  const response = await fetch(
    `http://localhost:3033/${searchType}?q=${encodeURIComponent(text)}`
  );
  if (!response.ok) {
    throw new Error("Failed to fetch results");
  }
  return response.json();
}

const performSearch = async (
  e: Parameters<BlockCommandCallback>[0],
  search: "text" | "fuzzy" | "first_each_word"
) => {
  const block = await logseq.Editor.getBlock(e.uuid);
  const ui = await logseq.Editor.getEditingCursorPosition();

  if (!block || !ui) return;

  const style = {
    left: ui.rect.left + 50 + "px",
    top: ui.rect.top + 50 + "px",
    width: "400px",
    position: "fixed",
    backgroundColor: "var(--ls-primary-background-color)",
  } as const;

  console.log("got block and ui", block, ui);

  // Show loading state
  logseq.provideUI({
    key: "gurbani-search-dialog",
    template: `<div style="padding: 20px;">Searching...</div>`,
    style,
    close: "outside",
    replace: true,
  });

  try {
    const matches = await searchDatabase(block.content, search);
    logseq.provideUI({
      key: "gurbani-search-dialog",
      template: dsl(matches, e.uuid),
      style,
      reset: true,
      close: "outside",
    });
  } catch (error) {
    console.error("Error searching:", error);
    logseq.provideUI({
      key: "gurbani-search-dialog",
      template: `<div style="padding: 20px;">Error searching: ${
        (error as any).message
      }</div>`,
      style,
      reset: true,
      close: "outside",
    });
  }

  logseq.provideModel({
    selectPankti: async function (arg: { dataset: { pankti: string } }) {
      const pankti = JSON.parse(arg.dataset.pankti);
      const uuid = e.uuid;
      const block = await logseq.Editor.getBlock(uuid);
      if (!block) return;

      await logseq.Editor.insertBlock(
        uuid,
        `${pankti.punjabi}\t{{cloze ${pankti.translit} ${pankti.attributes}}}`
      );
    },

    insertShabad: async function (arg: { dataset: { matches: string; uuid: string } }) {
      const matches = JSON.parse(arg.dataset.matches);
      const uuid = arg.dataset.uuid;
      const block = await logseq.Editor.getBlock(uuid);
      if (!block) return;

      // Insert all panktis one after another
      for (const pankti of matches) {
        await logseq.Editor.insertBlock(
          uuid,
          `${pankti.punjabi}\t{{cloze ${pankti.translit} ${pankti.attributes}}}`
        );
      }
    },

    viewShabad: async function (arg: {
      dataset: { shabadId: string; results: string };
    }) {
      const shabadId = arg.dataset.shabadId;
      const response = await fetch(
        `http://localhost:3033/get_shabad/${shabadId}`
      );
      const matches = await response.json();
      logseq.provideUI({
        key: "gurbani-search-dialog",
        reset: true,
        template: shabadDsl(matches, JSON.parse(arg.dataset.results), e.uuid),
        style,
      });
    },

    backToSearch: async function (arg: { dataset: { results: string } }) {
      const results = JSON.parse(arg.dataset.results);
      logseq.provideUI({
        key: "gurbani-search-dialog",
        reset: true,
        template: dsl(results, e.uuid),
        style,
      });
    },
  });
};

const main = () => {
  logseq.provideStyle(`
    #pankti-search {
      padding: 1em;
      width: 400px;
      height: 400px;
      margin: 0 auto;
    }
    #shabad-view {
      background: var(--ls-primary-background-color);
      padding: 2em;
      width: 400px;
      margin: 0 auto;
      height: 400px;
      overflow-y: auto;
    }
  `);

  logseq.Editor.registerSlashCommand(
    "🔍 Pankti (First Letter Start)",
    async (e) => {
      await performSearch(e, "first_each_word");
    }
  );

  logseq.Editor.registerSlashCommand("🔍 Pankti (Text)", async (e) => {
    await performSearch(e, "text");
  });

  logseq.Editor.registerSlashCommand("🔍 Pankti (Fuzzy)", async (e) => {
    await performSearch(e, "fuzzy");
  });
};

logseq.ready(main).catch(console.error);
