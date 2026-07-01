import { useNavigate } from 'react-router';
import AccountLookupDetail from '../../imports/AccountLookup-1';

export default function AccountDetailPage() {
  const navigate = useNavigate();

  const handleClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    const text = target.textContent || '';

    // Sidebar navigation
    if (text.includes('Back to Overview') || text.includes('← Back')) {
      navigate('/account-lookup');
    } else if (text.includes('Dashboard') && !text.includes('Account')) {
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
      <AccountLookupDetail />
    </div>
  );
}
