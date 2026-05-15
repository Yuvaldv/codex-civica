import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  lawsSidebar: [
    {
      type: 'category',
      label: 'State',
      collapsible: true,
      collapsed: false,
      items: [
        {type: 'doc', id: '147453', label: 'חוק-יסוד: הכנסת'},
        {type: 'doc', id: '147468', label: 'חוק הירושה'},
        {type: 'doc', id: '147449', label: 'חוק-יסוד: הממשלה'},
        {type: 'doc', id: '147391', label: 'חוק החוזים'},
        {type: 'doc', id: '174450', label: 'חוק-יסוד: השפיטה'},
        {type: 'doc', id: '149942', label: 'חוק שמירת הניקיון'},
        {type: 'doc', id: '151459', label: 'חוק שכר מינימום'},
        {type: 'doc', id: '174478', label: 'חוק זכויות החולה'},
        {type: 'doc', id: '163627', label: 'חוק חופש המידע'},
      ],
    },
    {
      type: 'html',
      value: '<div class="sidebar-section-header">Municipal</div>',
    },
  ],
};

export default sidebars;
