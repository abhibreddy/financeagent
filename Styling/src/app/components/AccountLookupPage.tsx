import { useNavigate } from 'react-router';
import AccountLookup from '../../imports/AccountLookup';

export default function AccountLookupPage() {
  const navigate = useNavigate();

  const handleClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    const text = target.textContent || '';
    const closestDiv = target.closest('[data-name="Table Row"]');

    // Sidebar navigation
    if (text.includes('Back to Overview') || text.includes('← Back')) {
      navigate('/');
    } else if (text.includes('Dashboard') && !text.includes('Account')) {
      navigate('/');
    } else if (text.includes('Alert Queue')) {
      navigate('/alert-queue');
    } else if (text.includes('Support Chat')) {
      navigate('/chat');
    }

    // View Details buttons or account cards
    else if (text.includes('View Details')) {
      e.stopPropagation();
      const rowElement = target.closest('[data-name="Table Row"]') || target.closest('[data-name="Container"]');
      const rowText = rowElement?.textContent || '';

      if (rowText.includes('ACC-00008')) {
        navigate('/account/00008');
      } else if (rowText.includes('ACC-00014')) {
        navigate('/account/00014');
      } else if (rowText.includes('ACC-00025')) {
        navigate('/account/00025');
      } else if (rowText.includes('ACC-00029')) {
        navigate('/account/00029');
      } else {
        navigate('/account/00008');
      }
    }

    // Account number clicks
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
      <AccountLookup />
    </div>
  );
}
