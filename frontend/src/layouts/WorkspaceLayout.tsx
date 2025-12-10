import React from 'react';

interface WorkspaceLayoutProps {
  sidebar: React.ReactNode;
  canvas: React.ReactNode;
  panel: React.ReactNode;
  header?: React.ReactNode;
}

export const WorkspaceLayout: React.FC<WorkspaceLayoutProps> = ({ sidebar, canvas, panel, header }) => {
  return (
    <div className="flex flex-col h-screen w-screen bg-pku-light">
      <header className="h-14 bg-white border-b border-gray-200 flex items-center px-4 shrink-0 z-10">
        {header || <span className="font-serif text-lg text-pku-red font-bold">AI-PPT Flow</span>}
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col overflow-y-auto shrink-0">
          <div className="p-4 space-y-4">{sidebar}</div>
        </aside>

        <main className="flex-1 bg-gray-100 relative flex flex-col min-w-0">
          <div className="flex-1 flex items-center justify-center p-8 overflow-auto">{canvas}</div>
        </main>

        <aside className="w-80 bg-white border-l border-gray-200 flex flex-col overflow-y-auto shrink-0 shadow-xl z-10">
          <div className="p-5 h-full">{panel}</div>
        </aside>
      </div>
    </div>
  );
};
