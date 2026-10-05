import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * RagResponseView
 * 
 * Professional RAG response component supporting:
 * 1. Clean GitHub-flavored Markdown (tables, headers, bold, blockquotes, lists, code)
 * 2. Clickable inline citations like [1], [2]
 * 3. Compact metadata badges [ SEMANTIC ] [ OPENROUTER ] [ 2 SOURCES ]
 * 4. Responsive bottom source cards with arrow indicators
 * 5. Slide-out provenance modal/drawer for deep inspection
 */
export function RagResponseView({ response }) {
  const [selectedCitation, setSelectedCitation] = useState(null);

  if (!response) return null;

  const { answer = "", citations = [], query_type = "SEMANTIC", metadata = {} } = response;
  const provider = metadata?.provider || "LLM";

  // Custom text renderer to transform inline citation markers [1], [2] into clickable chips
  const renderTextWithCitations = (children) => {
    if (typeof children !== 'string') return children;
    const parts = children.split(/(\[\d+\])/g);
    return parts.map((part, index) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const citationId = parseInt(match[1], 10);
        return (
          <button
            key={index}
            onClick={() => {
              const cit = citations.find(c => c.id === citationId) || citations[citationId - 1];
              if (cit) setSelectedCitation(cit);
            }}
            className="inline-flex items-center px-1.5 py-0.5 mx-0.5 text-xs font-bold rounded-full bg-sky-500/15 text-sky-400 border border-sky-500/30 hover:bg-sky-500 hover:text-slate-900 transition-all cursor-pointer align-baseline"
            title={`View source [${citationId}]`}
          >
            [{citationId}]
          </button>
        );
      }
      return part;
    });
  };

  return (
    <div className="flex flex-col gap-4 p-5 rounded-2xl bg-slate-900/90 border border-slate-800 text-slate-100 shadow-xl max-w-4xl relative">
      {/* 1. Header Badges */}
      <div className="flex items-center gap-2 pb-3 border-b border-slate-800/80 text-[11px] font-semibold tracking-wider uppercase">
        <span className="px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-400 border border-sky-500/30">
          {query_type}
        </span>
        <span className="px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30">
          {provider.toUpperCase()}
        </span>
        <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
          {citations.length} {citations.length === 1 ? 'SOURCE' : 'SOURCES'}
        </span>
      </div>

      {/* 2. Structured Markdown Body */}
      <div className="prose prose-invert prose-slate max-w-none text-sm leading-relaxed">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            p: ({ children }) => <p className="mb-3 leading-relaxed">{renderTextWithCitations(children)}</p>,
            li: ({ children }) => <li className="mb-1">{renderTextWithCitations(children)}</li>,
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-sky-400 bg-sky-500/5 px-4 py-2 my-3 rounded-r-lg text-slate-300">
                {children}
              </blockquote>
            ),
            table: ({ children }) => (
              <div className="overflow-x-auto my-3">
                <table className="w-full text-left border-collapse border border-slate-800 text-xs">
                  {children}
                </table>
              </div>
            ),
            th: ({ children }) => (
              <th className="bg-sky-500/10 text-sky-300 p-2.5 border border-slate-800 font-semibold">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="p-2.5 border border-slate-800">
                {children}
              </td>
            ),
          }}
        >
          {answer}
        </ReactMarkdown>
      </div>

      {/* 3. Bottom Source Cards */}
      {citations.length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-800">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5">
            Sources & Verified Provenance
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {citations.map((c) => (
              <div
                key={c.id}
                onClick={() => setSelectedCitation(c)}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-sky-500/50 hover:bg-sky-500/5 cursor-pointer transition-all group"
              >
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <span className="px-1.5 py-0.5 text-xs font-bold rounded bg-sky-500/20 text-sky-300">
                    [{c.id}]
                  </span>
                  <span className="text-base">📄</span>
                  <div className="overflow-hidden">
                    <div className="text-xs font-semibold text-slate-200 truncate group-hover:text-sky-300 transition-colors">
                      {c.source}
                    </div>
                    <div className="text-[11px] text-slate-400 truncate">
                      {c.title || c.snippet?.slice(0, 50) + '...'}
                    </div>
                  </div>
                </div>
                <span className="text-slate-500 group-hover:text-sky-400 group-hover:translate-x-0.5 transition-all text-sm ml-2">
                  &rarr;
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Slide-out Provenance Drawer / Modal */}
      {selectedCitation && (
        <div className="fixed inset-y-0 right-0 w-96 max-w-full bg-slate-900 border-l border-slate-800 shadow-2xl p-6 z-50 flex flex-col overflow-y-auto">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
              <span>📄</span> [{selectedCitation.id}] {selectedCitation.source}
            </h3>
            <button
              onClick={() => setSelectedCitation(null)}
              className="text-slate-400 hover:text-white p-1"
            >
              ✕
            </button>
          </div>

          <div className="my-4 space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Title</span>
              <span className="font-medium text-slate-200">{selectedCitation.title || 'N/A'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Status</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                selectedCitation.status === 'active'
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                  : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
              }`}>
                {selectedCitation.status || 'ACTIVE'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Event Date</span>
              <span className="font-medium text-slate-200">{selectedCitation.event_at ? selectedCitation.event_at.split('T')[0] : 'N/A'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Validity Window</span>
              <span className="font-medium text-slate-200">
                {selectedCitation.valid_from ? selectedCitation.valid_from.split('T')[0] : 'Start'} &rarr; {selectedCitation.valid_until ? selectedCitation.valid_until.split('T')[0] : 'Present'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Relevance Score</span>
              <span className="font-medium text-slate-200">{selectedCitation.score != null ? selectedCitation.score : 'N/A'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Chunk ID</span>
              <span className="font-medium text-slate-200">{selectedCitation.chunk_id || 'N/A'}</span>
            </div>
          </div>

          <div className="mt-2 flex-1">
            <span className="text-xs font-bold text-sky-400 uppercase tracking-wider block mb-2">
              Verified Grounded Excerpt
            </span>
            <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 leading-relaxed italic">
              "{selectedCitation.snippet || 'No excerpt available.'}"
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RagResponseView;
