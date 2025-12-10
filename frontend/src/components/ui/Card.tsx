import React from 'react';

export const Card: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className = '', ...props }) => {
  return (
    <div
      className={`bg-pku-paper rounded-lg border border-gray-100 shadow-academic ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
