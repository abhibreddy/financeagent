import { useNavigate } from 'react-router';
import ChatWithModal from '../../imports/Chat-2';

export default function ChatWithModalPage() {
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
    } else if (text.includes('Close') || text.includes('Cancel')) {
      navigate('/chat/active');
    }
  };

  return (
    <div onClick={handleClick} className="cursor-pointer">
      <ChatWithModal />
    </div>
  );
}
