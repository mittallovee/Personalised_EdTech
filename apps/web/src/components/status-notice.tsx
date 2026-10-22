/** A short message that something went through ("Anita Rao was removed."). */
export function StatusNotice({ children }: { children: string }) {
  return (
    <p
      role="status"
      className="mb-6 max-w-2xl rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
    >
      {children}
    </p>
  );
}
