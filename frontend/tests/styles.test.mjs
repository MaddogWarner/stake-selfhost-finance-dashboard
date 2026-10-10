import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import test from 'node:test';
import postcss from 'postcss';

// Inspect Vite's actual output, so a successful build with missing utilities fails.
const assets = new URL('../dist/assets/', import.meta.url);
const cssFiles = readdirSync(assets).filter((name) => name.endsWith('.css'));
assert.equal(cssFiles.length, 1);
const css = postcss.parse(readFileSync(new URL(cssFiles[0], assets), 'utf8'));

function declarations(selector, property) {
  const values = [];
  css.walkRules((rule) => {
    if (rule.selector === selector) {
      rule.walkDecls(property, (decl) => values.push(decl.value));
    }
  });
  return values;
}

function hasDeclaration(selector, property, value) {
  assert.ok(declarations(selector, property).includes(value), `${selector}: ${property} = ${value}`);
}

test('dashboard layout and colours survive production CSS generation', () => {
  hasDeclaration('.flex', 'display', 'flex');
  hasDeclaration('.bg-slate-900', 'background-color', 'var(--color-slate-900)');
  hasDeclaration('.rounded', 'border-radius', '.25rem');
  hasDeclaration('.md\\:flex-row', 'flex-direction', 'row');
  hasDeclaration('.sm\\:grid-cols-2', 'grid-template-columns', 'repeat(2,minmax(0,1fr))');
});

test('cards retain the v3 small shadow', () => {
  assert.ok(declarations('.shadow-xs', '--tw-shadow').some((value) => value.startsWith('0 1px 2px 0 ')));
});

test('forms retain focus rings and an outline in forced-colours mode', () => {
  assert.ok(declarations('.focus\\:ring-1:focus', '--tw-ring-shadow').some((value) => value.includes('calc(1px +')));
  let forcedOutline = false;
  css.walkAtRules('media', (media) => {
    if (media.params === '(forced-colors:active)') {
      media.walkRules((rule) => {
        if (rule.selector === '.focus\\:outline-hidden:focus') {
          rule.walkDecls('outline', (decl) => { forcedOutline ||= decl.value === '2px solid #0000'; });
        }
      });
    }
  });
  assert.ok(forcedOutline, 'focused inputs need an outline in forced-colours mode');
});

test('form defaults and disabled controls survive the upgrade', () => {
  hasDeclaration('input::placeholder,textarea::placeholder', 'color', 'var(--color-gray-400)');
  hasDeclaration('button:not(:disabled),[role=button]:not(:disabled)', 'cursor', 'pointer');
  hasDeclaration('.disabled\\:bg-slate-700:disabled', 'background-color', 'var(--color-slate-700)');
});
