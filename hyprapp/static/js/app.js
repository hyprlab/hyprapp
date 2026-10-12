/* Hyprapp client: native ES modules, no dependencies, no build step.
 *
 * Each module guards on the elements it needs. A feature that nothing else
 * imports (theme, sidebar drawer, settings, preferences, admin, turnstile,
 * menus, the palette, paging, pull to refresh, about) is removed by deleting
 * its module and its line here; api, dom, toast, dialogs, restore, records
 * and record-form are shared. The order is the order they set up in;
 * restoreDialogs() runs last, once every dialog has registered what it
 * remembers across a reload. Every module URL is versioned by the import map
 * in base.html, so a redeploy is never served from a stale cache.
 */
import "./theme.js";
import "./sidebar.js";
import "./dialogs.js";
import "./settings.js";
import "./preferences.js";
import "./admin.js";
import "./turnstile.js";
import "./menus.js";
import "./records.js";
import "./record-form.js";
import "./sheet.js";
import "./palette.js";
import "./paging.js";
import "./pull-to-refresh.js";
import "./about.js";
import { restoreDialogs } from "./restore.js";

restoreDialogs();
