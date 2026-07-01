import { useNavigate } from 'react-router';
import ChatActive from '../../imports/Chat-1';

export default function ChatActivePage() {
  const navigate = useNavigate();

  const handleClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    const text = target.textContent || '';

    if (text.includes('Dashboard')) {
      navigate('/');
    } else if (text.includes('Account Lookup')) {
      navigate('/account-lookup');
    } else if (text.includes('Alert Queue')) {
      navigate('/alert-queue');
    } else if (text.includes('Support Chat')) {
      navigate('/chat');
    }
  };

  return (
    <div onClick={handleClick} className="cursor-pointer">
      <ChatActive />
    </div>
  );
}
