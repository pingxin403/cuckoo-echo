import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { Message } from '@/types';

// Mock complex dependencies before importing the component
vi.mock('@/pages/chat/FeedbackPanel', () => ({
  default: () => <div data-testid="feedback-panel">FeedbackPanel</div>,
}));

vi.mock('@/pages/chat/ImageLightbox', () => ({
  default: () => <div data-testid="image-lightbox">ImageLightbox</div>,
}));

vi.mock('@/network/axios', () => ({
  default: { post: vi.fn() },
}));

vi.mock('@/components/Toast', () => ({
  showToast: vi.fn(),
}));

import MessageBubble from '@/pages/chat/MessageBubble';

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: 'msg-1',
    threadId: 'thread-1',
    role: 'user',
    content: 'Hello world',
    createdAt: '2024-01-01T12:00:00Z',
    ...overrides,
  };
}

describe('MessageBubble', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders user message right-aligned with brand color', () => {
    const msg = makeMessage({ role: 'user', content: 'Hi there' });
    render(<MessageBubble message={msg} />);

    const bubble = screen.getByTestId('message-bubble');
    // User messages should be right-aligned (justify-end)
    expect(bubble.className).toContain('justify-end');

    // The inner div should have the brand color class
    const inner = bubble.firstElementChild as HTMLElement;
    expect(inner.className).toContain('bg-[var(--ce-primary-color,#4f46e5)]');
    expect(inner.className).toContain('text-white');

    expect(screen.getByText('Hi there')).toBeInTheDocument();
  });

  it('renders assistant message with Markdown content', () => {
    const msg = makeMessage({
      role: 'assistant',
      content: '**bold text** and `code`',
    });
    render(<MessageBubble message={msg} />);

    const bubble = screen.getByTestId('message-bubble');
    // Assistant messages should be left-aligned (justify-start)
    expect(bubble.className).toContain('justify-start');

    // react-markdown renders **bold** as <strong>
    expect(screen.getByText('bold text')).toBeInTheDocument();
    expect(screen.getByText('code')).toBeInTheDocument();
  });

  it('renders human_agent message with "人工客服" badge', () => {
    const msg = makeMessage({
      role: 'human_agent',
      content: 'I am a human agent',
    });
    render(<MessageBubble message={msg} />);

    expect(screen.getByText('人工客服')).toBeInTheDocument();

    const bubble = screen.getByTestId('message-bubble');
    const inner = bubble.firstElementChild as HTMLElement;
    expect(inner.className).toContain('bg-green-100');
  });

  it('shows feedback buttons (👍/👎) for assistant messages only', () => {
    // Assistant message should have feedback buttons
    const assistantMsg = makeMessage({ role: 'assistant', content: 'AI reply' });
    const { unmount } = render(<MessageBubble message={assistantMsg} />);

    expect(screen.getByLabelText('点赞')).toBeInTheDocument();
    expect(screen.getByLabelText('点踩')).toBeInTheDocument();
    unmount();

    // User message should NOT have feedback buttons
    const userMsg = makeMessage({ role: 'user', content: 'User msg' });
    render(<MessageBubble message={userMsg} />);

    expect(screen.queryByLabelText('点赞')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('点踩')).not.toBeInTheDocument();
  });

  it('shows TypingIndicator dots when isStreaming and no content', () => {
    const msg = makeMessage({ role: 'assistant', content: '' });
    render(
      <MessageBubble message={msg} isStreaming streamingContent="" />,
    );

    // TypingIndicator has aria-label="正在输入"
    expect(screen.getByLabelText('正在输入')).toBeInTheDocument();
  });
});
