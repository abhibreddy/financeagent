import { useNavigate } from 'react-router';
import Dashboard from '../../imports/Dashboard';

export default function DashboardPage() {
  const navigate = useNavigate();

  const handleClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    const text = target.textContent || '';
    const closestParagraph = target.closest('p');
    const paragraphText = closestParagraph?.textContent || '';

    // Sidebar navigation
    if (text.includes('Account Lookup') || paragraphText.includes('Account Lookup')) {
      navigate('/account-lookup');
    } else if (text.includes('Alert Queue') || paragraphText.includes('Alert Queue')) {
      navigate('/alert-queue');
    } else if (text.includes('Support Chat') || paragraphText.includes('Support Chat')) {
      navigate('/chat');
    } else if (text.includes('Dashboard') && !text.includes('Account')) {
      navigate('/');
    }

    // Account rows - navigate to account detail
    else if (text.includes('ACC-00014') || text.includes('James Powers')) {
      navigate('/account/00014');
    } else if (text.includes('ACC-00025') || text.includes('Daniel Perry')) {
      navigate('/account/00025');
    } else if (text.includes('ACC-00029') || text.includes('Michael Burton')) {
      navigate('/account/00029');
    } else if (text.includes('ACC-00093')) {
      navigate('/account/00093');
    }

    // Alert cards
    else if (text.includes('Velocity Alerts') || text.includes('Geo Anomaly Alerts') || text.includes('Dead Stock Risk')) {
      navigate('/alert-queue');
    }
  };

  return (
    <div onClick={handleClick} className="cursor-pointer">
      <Dashboard />
    </div>
  );
}
