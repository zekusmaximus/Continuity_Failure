interface StatusTagProps {
  label: string;
  className: string;
  title?: string;
}

/** A small diegetic status pill (urgency / public-status / reliability / etc). */
export default function StatusTag({ label, className, title }: StatusTagProps) {
  return (
    <span className={`status-tag ${className}`} title={title}>
      {label}
    </span>
  );
}
