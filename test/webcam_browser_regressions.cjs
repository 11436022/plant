'use strict';

// Run with: node --test test/webcam_browser_regressions.cjs
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const templatePath = join(__dirname, '..', 'templates', 'webcam.html');
const html = readFileSync(templatePath, 'utf8');
const inline = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]
    .filter((match) => !/\bsrc\s*=/i.test(match[1]));
assert.equal(inline.length, 1, 'Expected one inline webcam application script');
const script = new vm.Script(inline[0][2], { filename: templatePath });

function deferred() {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}

function response(sessionId, triggered = false) {
    return {
        diagnosis: { crop_name: 'Tomato', status_name: 'Spot', confidence: 0.95 },
        monitoring: { session_id: sessionId, region_id: 'full-frame', triggered, streak: 3, required_matches: 3 },
        alert: { id: 1, session_id: sessionId, region_id: 'full-frame' },
    };
}

function harness() {
    const nodes = new Map();
    const calls = { api: [], render: [], alarms: [], history: [], intervals: [], clears: [], permissions: 0, blobs: 0 };
    const hooks = {};
    const storage = new Map();
    let uuid = 0;
    const element = (id) => {
        if (!nodes.has(id)) {
            nodes.set(id, {
                value: id === 'intervalInput' ? '30' : '', textContent: '', innerHTML: '',
                hidden: false, disabled: false, className: '', style: {}, listeners: new Map(),
                addEventListener(type, callback) { this.listeners.set(type, callback); },
                replaceChildren(...children) { this.children = children; },
            });
        }
        return nodes.get(id);
    };
    Object.assign(element('cameraVideo'), { videoWidth: 640, videoHeight: 480, play: async () => {} });
    Object.assign(element('captureCanvas'), {
        getContext: () => ({ drawImage() {} }),
        toBlob(callback) {
            calls.blobs += 1;
            if (hooks.blob) hooks.blob(callback);
            else callback({ type: 'image/jpeg', size: 128 });
        },
    });
    class FormDataMock {
        constructor() { this.entries = []; }
        append(...entry) { this.entries.push(entry); }
        get(name) { return this.entries.find((entry) => entry[0] === name)?.[1] ?? null; }
    }
    class NotificationMock {
        static permission = 'granted';
        static requestPermission() {
            calls.permissions += 1;
            return hooks.permission ? hooks.permission() : Promise.resolve('granted');
        }
        constructor() { assert.fail('Alarm effects should be observed through the fireAlarm spy'); }
    }
    const window = {
        Notification: NotificationMock,
        addEventListener() {},
        setInterval(callback, delay) {
            const id = calls.intervals.length + 1;
            calls.intervals.push({ id, callback, delay });
            return id;
        },
        clearInterval(id) { calls.clears.push(id); },
    };
    const context = vm.createContext({
        window, Notification: NotificationMock, FormData: FormDataMock,
        crypto: { randomUUID: () => `session-${++uuid}` },
        document: { getElementById: element, createElement: (tag) => element(`created-${tag}`) },
        localStorage: {
            getItem: (key) => storage.get(key) ?? null,
            setItem: (key, value) => storage.set(key, value),
            removeItem: (key) => storage.delete(key),
        },
        fetch() { assert.fail('Network requests are forbidden in this harness'); },
        navigator: { mediaDevices: {} },
    });
    script.runInContext(context, { timeout: 1000 });
    const state = vm.runInContext('state', context);
    state.stream = { getTracks: () => [{ stop() {} }] };
    state.settings = { required_matches: 3 };
    Object.assign(context, {
        __api(path, options) {
            calls.api.push({ path, options });
            assert.equal(path, '/webcam/analyze');
            return hooks.api ? hooks.api(path, options) : Promise.resolve(response(state.sessionId));
        },
        __render(payload) { calls.render.push(payload); },
        __alarm(alert) { calls.alarms.push(alert); },
        __history() {
            calls.history.push(true);
            return hooks.history ? hooks.history() : Promise.resolve();
        },
    });
    // Replace only side effects, keeping the production capture/start/stop control flow.
    vm.runInContext(`
        api = (...args) => __api(...args);
        renderDiagnosis = (...args) => __render(...args);
        fireAlarm = (...args) => __alarm(...args);
        loadAlerts = (...args) => __history(...args);
    `, context);
    return {
        state, calls, hooks, element, Notification: NotificationMock,
        capture: vm.runInContext('captureFrame', context),
        start: vm.runInContext('startMonitoring', context),
        stop: vm.runInContext('stopMonitoring', context),
        stopCamera: vm.runInContext('stopCamera', context),
    };
}

function uiState(h) {
    return {
        status: h.element('monitorStatus').textContent,
        mode: h.element('statusDot').className,
        error: h.element('monitorError').textContent,
        lastScan: h.element('lastScan').textContent,
        monitorDisabled: h.element('monitorButton').disabled,
        cameraDisabled: h.element('cameraButton').disabled,
    };
}

function stopAndMark(h) {
    h.stop();
    h.element('monitorError').textContent = 'Current session message';
    h.element('lastScan').textContent = 'Current session scan';
    return uiState(h);
}

function assertNoAlarm(h) {
    assert.equal(h.calls.alarms.length, 0);
    assert.equal(h.calls.history.length, 0);
}

for (const blob of [{ type: 'image/jpeg' }, null]) {
    test(`stop during toBlob ignores its late ${blob ? 'image' : 'null'} result`, async () => {
        const h = harness();
        let finishBlob;
        h.hooks.blob = (callback) => { finishBlob = callback; };
        const pending = h.capture();
        assert.equal(h.state.analyzing, true);
        const stopped = stopAndMark(h);
        finishBlob(blob);
        await pending;
        assert.equal(h.calls.api.length, 0);
        assert.equal(h.calls.render.length, 0);
        assertNoAlarm(h);
        assert.deepEqual(uiState(h), stopped);
        assert.equal(h.state.analyzing, false);
    });
}

for (const fails of [false, true]) {
    test(`stale analysis ${fails ? 'error' : 'response'} cannot overwrite the stopped session`, async () => {
        const h = harness();
        const request = deferred(), entered = deferred();
        const sessionId = h.state.sessionId;
        h.hooks.api = () => { entered.resolve(); return request.promise; };
        const pending = h.capture();
        await entered.promise;
        const stopped = stopAndMark(h);
        if (fails) request.reject(new Error('Obsolete analysis error'));
        else request.resolve(response(sessionId, true));
        await pending;
        assert.equal(h.calls.api.length, 1);
        assert.equal(h.calls.render.length, 0);
        assertNoAlarm(h);
        assert.deepEqual(uiState(h), stopped);
        assert.equal(h.state.analyzing, false);
    });
}

for (const stopMethod of ['stop', 'stopCamera']) {
    test(`${stopMethod} while notification permission is pending prevents capture and timer`, async () => {
        const h = harness();
        const permission = deferred();
        h.Notification.permission = 'default';
        h.hooks.permission = () => permission.promise;
        const pending = h.start();
        assert.equal(h.calls.permissions, 1);
        h[stopMethod]();
        const stopped = uiState(h);
        permission.resolve('granted');
        await pending;
        assert.equal(h.calls.blobs, 0);
        assert.equal(h.calls.api.length, 0);
        assert.equal(h.calls.intervals.length, 0);
        assert.equal(h.state.timer, null);
        assertNoAlarm(h);
        assert.deepEqual(uiState(h), stopped);
    });
}

test('active permission completion captures once and starts a bounded timer', async () => {
    const h = harness();
    const permission = deferred();
    h.Notification.permission = 'default';
    h.hooks.permission = () => permission.promise;
    h.element('intervalInput').value = '999';
    const pending = h.start();
    assert.equal(h.calls.api.length, 0);
    permission.resolve('granted');
    await pending;
    assert.equal(h.calls.blobs, 1);
    assert.equal(h.calls.api.length, 1);
    assert.equal(h.calls.render.length, 1);
    assert.equal(h.calls.intervals.length, 1);
    assert.equal(h.calls.intervals[0].delay, 600000);
    assert.equal(typeof h.calls.intervals[0].callback, 'function');
    assert.equal(h.state.timer, 1);
    h.stop();
    assert.deepEqual(h.calls.clears, [1]);
});

for (const mismatch of ['missing', 'session', 'region']) {
    test(`rejects ${mismatch} monitoring echo before diagnosis or alarm`, async () => {
        const h = harness();
        const payload = response(h.state.sessionId, true);
        if (mismatch === 'missing') delete payload.monitoring;
        else if (mismatch === 'session') payload.monitoring.session_id = 'other-session';
        else payload.monitoring.region_id = 'other-region';
        h.hooks.api = async () => payload;
        h.element('lastScan').textContent = 'Unchanged';
        await h.capture();
        assert.equal(h.calls.api.length, 1);
        assert.equal(h.calls.render.length, 0);
        assertNoAlarm(h);
        assert.notEqual(h.element('monitorError').textContent, '');
        assert.equal(h.element('lastScan').textContent, 'Unchanged');
        assert.equal(h.state.analyzing, false);
    });
}

for (const mismatch of ['not-triggered', 'session', 'region', 'missing-alert']) {
    test(`${mismatch} alert never fires a message or reloads alert history`, async () => {
        const h = harness();
        const payload = response(h.state.sessionId, true);
        if (mismatch === 'not-triggered') payload.monitoring.triggered = false;
        else if (mismatch === 'session') payload.alert.session_id = 'other-session';
        else if (mismatch === 'region') payload.alert.region_id = 'other-region';
        else payload.alert = null;
        h.hooks.api = async () => payload;
        await h.capture();
        assert.equal(h.calls.render.length, 1);
        assertNoAlarm(h);
        assert.equal(h.element('monitorError').textContent, '');
        assert.equal(h.element('statusDot').className, 'status-dot live');
        assert.equal(h.state.analyzing, false);
    });
}

test('matching triggered alert fires exactly once and preserves request scope', async () => {
    const h = harness();
    const payload = response(h.state.sessionId, true);
    h.hooks.api = async () => payload;
    await h.capture();
    assert.equal(h.calls.render.length, 1);
    assert.deepEqual(h.calls.alarms, [payload.alert]);
    assert.equal(h.calls.history.length, 1);
    assert.equal(h.calls.api[0].options.method, 'POST');
    const form = h.calls.api[0].options.body;
    assert.equal(form.get('session_id'), h.state.sessionId);
    assert.equal(form.get('region_id'), 'full-frame');
    assert.equal(form.get('file').type, 'image/jpeg');
    assert.equal(h.element('statusDot').className, 'status-dot alert');
    assert.equal(h.element('monitorError').textContent, '');
});

for (const fails of [false, true]) {
    test(`stopping during history ${fails ? 'failure' : 'success'} cannot revive stale status`, async () => {
        const h = harness();
        const history = deferred(), entered = deferred();
        h.hooks.api = async () => response(h.state.sessionId, true);
        h.hooks.history = () => { entered.resolve(); return history.promise; };
        const pending = h.capture();
        await entered.promise;
        assert.equal(h.calls.alarms.length, 1);
        const stopped = stopAndMark(h);
        if (fails) history.reject(new Error('Obsolete history error'));
        else history.resolve();
        await pending;
        assert.deepEqual(uiState(h), stopped);
        assert.equal(h.calls.alarms.length, 1);
        assert.equal(h.calls.history.length, 1);
        assert.equal(h.state.analyzing, false);
    });
}

test('current-session API errors remain visible and release the analyzing flag', async () => {
    const h = harness();
    h.hooks.api = async () => { throw new Error('Current failure'); };
    await h.capture();
    assert.equal(h.element('monitorError').textContent, 'Current failure');
    assert.equal(h.calls.render.length, 0);
    assertNoAlarm(h);
    assert.equal(h.state.analyzing, false);
});
