import type { ReviewEvent } from '../types';

type Props = {
  events: ReviewEvent[];
};

export function EventTimeline({ events }: Props) {
  return (
    <section className="panel timeline-panel">
      <div className="panel-heading">
        <h2>Realtime Events</h2>
        <span>{events.length}</span>
      </div>
      <div className="timeline">
        {events.length === 0 ? (
          <p className="muted">No events yet.</p>
        ) : (
          events.map((event, index) => (
            <div
              className={`timeline-item ${event.event === 'error' ? 'event-error' : ''}`}
              key={`${event.receivedAt}-${index}`}
            >
              <div className="timeline-meta">
                <strong>{event.event}</strong>
                <span>{event.node ?? 'unknown'}</span>
                <span>{event.receivedAt}</span>
              </div>
              <div>{event.message}</div>
              {event.error && <div className="error-text">{event.error}</div>}
            </div>
          ))
        )}
      </div>
    </section>
  );
}
