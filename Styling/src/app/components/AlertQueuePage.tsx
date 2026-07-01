import { useNavigate } from 'react-router';
import AlertQueue from '../../imports/AlertQueue';

export default function AlertQueuePage() {
  const navigate = useNavigate();

  const handleClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    const text = target.textContent || '';
    const closestDiv = target.closest('[data-name="Table Row"]');

    // Sidebar navigation
    if (text.includes('Dashboard') && !text.includes('Account')) {
      navigate('/');
    } else if (text.includes('Account Lookup')) {
      navigate('/account-lookup');
    } else if (text.includes('Support Chat')) {
      navigate('/chat');
    } else if (text.includes('Back to Overview') || text.includes('← Back')) {
      navigate('/');
    }

    // Alert row clicks - navigate to relevant account
    else if (text.includes('ACC-00008') || (closestDiv && closestDiv.textContent?.includes('ACC-00008'))) {
      navigate('/account/00008');
    } else if (text.includes('ACC-00014') || (closestDiv && closestDiv.textContent?.includes('ACC-00014'))) {
      navigate('/account/00014');
    } else if (text.includes('ACC-00025') || (closestDiv && closestDiv.textContent?.includes('ACC-00025'))) {
      navigate('/account/00025');
    } else if (text.includes('ACC-00029') || (closestDiv && closestDiv.textContent?.includes('ACC-00029'))) {
      navigate('/account/00029');
    }
  };

  return (
    <div onClick={handleClick} className="cursor-pointer">
      <AlertQueue />
    </div>
  );
}
