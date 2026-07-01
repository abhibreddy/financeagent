import { useNavigate } from 'react-router';
import Chat from '../../imports/Chat';

export default function ChatPage() {
  const navigate = useNavigate();

  const handleClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    const text = target.textContent || '';

    // Sidebar navigation
    if (text.includes('Dashboard') && !text.includes('Account')) {
      navigate('/');
    } else if (text.includes('Account Lookup')) {
      navigate('/account-lookup');
    } else if (text.includes('Alert Queue')) {
      navigate('/alert-queue');
    } else if (text.includes('Support Chat')) {
      navigate('/chat');
    }

    // Chat interactions - navigate to active chat state
    else if (text.includes('Send') || text.includes('Type a message')) {
      navigate('/chat/active');
    }
  };

  return (
    <div onClick={handleClick} className="cursor-pointer">
      <Chat />
    </div>
  );
}
