import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatInput from '@/pages/chat/ChatInput';

describe('ChatInput', () => {
  it('renders textarea and send button', () => {
    render(<ChatInput onSend={vi.fn()} />);

    expect(screen.getByLabelText('消息输入框')).toBeInTheDocument();
    expect(screen.getByLabelText('发送消息')).toBeInTheDocument();
  });

  it('Enter key calls onSend with trimmed text', () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByLabelText('消息输入框');
    fireEvent.change(textarea, { target: { value: '  hello world  ' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(onSend).toHaveBeenCalledWith('hello world', undefined);
  });

  it('Shift+Enter does NOT call onSend', () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByLabelText('消息输入框');
    fireEvent.change(textarea, { target: { value: 'hello' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });

    expect(onSend).not.toHaveBeenCalled();
  });

  it('disabled state shows "AI 正在思考…" and disables send button', () => {
    render(<ChatInput onSend={vi.fn()} disabled />);

    expect(screen.getByText('AI 正在思考…')).toBeInTheDocument();
    expect(screen.getByLabelText('发送消息')).toBeDisabled();
  });
});
