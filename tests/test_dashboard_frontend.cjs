// Testa o script real com DOM e Leaflet simulados; não requer pacotes npm.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../dashboard_v1/templates/index.html'), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
const elements = {};
const element = id => elements[id] ??= {
    value: id === 'filtro-busca' ? '' : id === 'filtro-empresa' ? 'TODAS' : 'TODOS',
    style: {}, children: [], appendChild(child) { this.children.push(child); },
};
let markerCount = 0;
let focusCount = 0;
const map = { setView() { focusCount++; return this; }, fitBounds() {} };
const layer = { addTo() { return this; }, clearLayers() {}, addLayer() { markerCount++; } };
const context = vm.createContext({
    document: { getElementById: element, createElement: () => ({}) },
    L: { map: () => map, tileLayer: () => layer, layerGroup: () => layer,
        divIcon: x => x, marker: () => ({ bindPopup() {} }) },
    EventSource: function () {}, fetch: () => new Promise(() => {}),
});
vm.runInContext(script, context);
vm.runInContext(`dadosGlobais = { radares: [
    { serie: 'A', empresa: 'E', municipio: 'M', local: 'Rua', lat: -23, lng: -46, faixas: 2, validade: '01/01/2020' },
    { serie: 'B', empresa: 'E', municipio: 'M', local: 'Rua', lat: null, lng: null, faixas: 0, validade: 'N/A' }
] }; aplicarFiltros();`, context);
assert.equal(markerCount, 1);
assert.equal(element('kpi-tab-total').innerText, 2);
assert.equal(element('kpi-tab-faixas').innerText, 2);
assert.match(element('label-mapa-count').innerText, /1 radares plotados · 1 sem coordenadas/);
assert.match(element('tbody-radares').children[1].innerHTML, /Sem coordenadas/);
assert.doesNotMatch(element('tbody-radares').children[1].innerHTML, /<a href=/);
vm.runInContext('focarNoMapa(null, null, "B")', context);
assert.equal(focusCount, 1); // Somente a posição inicial do mapa.
vm.runInContext('evt.onmessage({ data: "[PROCESSO FALHOU]" })', context);
assert.match(element('terminal-label-txt').innerText, /Falha/);
assert.equal(element('btn-atualizar-base').disabled, false);
console.log('OK: tabela, mapa, faixas e indicação de falha.');
