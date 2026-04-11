/**
 * Tests for the SSE stream parser in api.js.
 * We extract and test the parsing logic directly.
 */
import { describe, it, expect, vi } from 'vitest';

/**
 * Simulate the SSE parsing loop from api.js.
 * Takes an array of raw network chunks (strings), returns parsed events.
 */
function parseSSEChunks(chunks) {
  const events = [];
  let buffer = '';
  for (const chunk of chunks) {
    buffer += chunk;
    const parts = buffer.split('\n\n');
    buffer = parts.pop();
    for (const part of parts) {
      for (const line of part.split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            events.push(event);
          } catch (e) {
            // malformed — skipped
          }
        }
      }
    }
  }
  return events;
}

describe('SSE stream parser', () => {
  it('parses a single complete event in one chunk', () => {
    const chunks = ['data: {"type":"stage1_start"}\n\n'];
    const events = parseSSEChunks(chunks);
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('stage1_start');
  });

  it('parses multiple events in one chunk', () => {
    const chunks = [
      'data: {"type":"stage1_start"}\n\ndata: {"type":"stage1_complete","data":[]}\n\n',
    ];
    const events = parseSSEChunks(chunks);
    expect(events).toHaveLength(2);
    expect(events[0].type).toBe('stage1_start');
    expect(events[1].type).toBe('stage1_complete');
  });

  it('handles event split across two network chunks (the bug we fixed)', () => {
    const full = 'data: {"type":"stage1_complete","data":[{"model":"gpt-4o","response":"hi"}]}\n\n';
    const mid = Math.floor(full.length / 2);
    const chunks = [full.slice(0, mid), full.slice(mid)];
    const events = parseSSEChunks(chunks);
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('stage1_complete');
    expect(events[0].data[0].model).toBe('gpt-4o');
  });

  it('handles event split at data: boundary', () => {
    const chunks = ['data: {"type"', ':"stage2_start"}\n\n'];
    const events = parseSSEChunks(chunks);
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('stage2_start');
  });

  it('silently drops malformed JSON, keeps parsing rest', () => {
    const chunks = [
      'data: NOT_JSON\n\ndata: {"type":"complete"}\n\n',
    ];
    const events = parseSSEChunks(chunks);
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('complete');
  });

  it('ignores non-data lines (comment lines, blank lines)', () => {
    const chunks = [': keep-alive\n\ndata: {"type":"stage3_start"}\n\n'];
    const events = parseSSEChunks(chunks);
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('stage3_start');
  });

  it('returns empty array for empty stream', () => {
    expect(parseSSEChunks([])).toHaveLength(0);
    expect(parseSSEChunks([''])).toHaveLength(0);
  });

  it('handles all 6 real event types in sequence', () => {
    const types = [
      'stage1_start', 'stage1_complete',
      'stage2_start', 'stage2_complete',
      'stage3_start', 'stage3_complete',
    ];
    const chunks = [
      types.map(t => `data: {"type":"${t}"}\n\n`).join(''),
    ];
    const events = parseSSEChunks(chunks);
    expect(events.map(e => e.type)).toEqual(types);
  });

  it('handles title_complete and complete events', () => {
    const chunks = [
      'data: {"type":"title_complete","data":{"title":"Test Title"}}\n\ndata: {"type":"complete"}\n\n',
    ];
    const events = parseSSEChunks(chunks);
    expect(events).toHaveLength(2);
    expect(events[0].data.title).toBe('Test Title');
    expect(events[1].type).toBe('complete');
  });

  it('handles large payload split across many tiny chunks', () => {
    const payload = JSON.stringify({
      type: 'stage1_complete',
      data: Array.from({ length: 10 }, (_, i) => ({ model: `model-${i}`, response: 'x'.repeat(100) })),
    });
    const full = `data: ${payload}\n\n`;
    const chunks = full.split('').reduce((acc, char, i) => {
      const idx = Math.floor(i / 5);
      acc[idx] = (acc[idx] || '') + char;
      return acc;
    }, []);
    const events = parseSSEChunks(chunks);
    expect(events).toHaveLength(1);
    expect(events[0].data).toHaveLength(10);
  });
});
