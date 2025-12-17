import React from 'react';
import { type Memory } from '../api/memoryApi';
import { ImageIcon, CheckCircle } from 'lucide-react';
import clsx from 'clsx';
import { format } from 'date-fns';

interface MemoryCardProps {
  memory: Memory;
  onClick: (memory: Memory) => void;
  selected?: boolean;
  selectionMode?: boolean;
}

export const MemoryCard: React.FC<MemoryCardProps> = ({ memory, onClick, selected, selectionMode }) => {
  return (
    <div
      onClick={() => onClick(memory)}
      className={clsx(
        "group relative aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer transition-all border-2",
        selected
          ? "border-blue-600 ring-2 ring-blue-200 shadow-md"
          : "border-transparent hover:shadow-md"
      )}
    >
      {memory.thumbnail_b64 ? (
        <img
          src={memory.thumbnail_b64}
          alt={memory.summary || "Memory"}
          className={clsx(
            "w-full h-full object-cover transition-transform duration-300",
            !selected && "group-hover:scale-105"
          )}
          loading="lazy"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-gray-400">
          <ImageIcon className="w-8 h-8" />
        </div>
      )}

      {/* Selection Indicator */}
      {selectionMode && (
        <div className={clsx(
          "absolute top-2 right-2 rounded-full p-1 transition-all",
          selected ? "bg-blue-600 text-white" : "bg-black/30 text-white/50 hover:bg-black/50"
        )}>
          <CheckCircle className="w-5 h-5" fill={selected ? "currentColor" : "none"} />
        </div>
      )}

      {/* Overlay info on hover (hidden if selected or in selection mode to reduce clutter) */}
      {!selectionMode && (
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <p className="text-white text-xs font-medium line-clamp-2">
            {memory.summary || "No summary available"}
          </p>
          {memory.exif_date && (
             <p className="text-white/80 text-[10px] mt-1">
               {format(new Date(memory.exif_date), 'MMM d, yyyy')}
             </p>
          )}
        </div>
      )}
    </div>
  );
};
