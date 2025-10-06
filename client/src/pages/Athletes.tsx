import React, { useState, useEffect } from 'react';
import { 
  Table, 
  Input, 
  Button, 
  Space, 
  Card, 
  Typography, 
  Tag, 
  message,
  Spin,
  Modal,
  Descriptions
} from 'antd';
import { SearchOutlined, EyeOutlined, UserOutlined, CalendarOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title } = Typography;
const { Search } = Input;

interface Athlete {
  id: number;
  family_name: string;
  given_name: string;
  full_name: string;
  birth_date: string;
  gender: string;
  country_name: string;
  disciplines: string[];
}

const Athletes: React.FC = () => {
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const [selectedAthlete, setSelectedAthlete] = useState<Athlete | null>(null);
  const [modalVisible, setModalVisible] = useState(false);

  useEffect(() => {
    fetchAthletes();
  }, [pagination.current, pagination.pageSize, searchText]);

  const fetchAthletes = async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:5000/api/athletes', {
        params: {
          page: pagination.current,
          per_page: pagination.pageSize,
          search: searchText || undefined,
        },
      });

      setAthletes(response.data.athletes);
      setPagination(prev => ({
        ...prev,
        total: response.data.total,
      }));
    } catch (error) {
      message.error('Failed to fetch athletes');
      console.error('Error fetching athletes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTableChange = (newPagination: any) => {
    setPagination(prev => ({
      ...prev,
      current: newPagination.current,
      pageSize: newPagination.pageSize,
    }));
  };

  const handleSearch = (value: string) => {
    setSearchText(value);
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  const showAthleteDetails = (athlete: Athlete) => {
    setSelectedAthlete(athlete);
    setModalVisible(true);
  };

  const calculateAge = (birthDate: string) => {
    const today = new Date();
    const birth = new Date(birthDate);
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  };

  const columns = [
    {
      title: 'Name',
      key: 'name',
      render: (record: Athlete) => (
        <Space>
          <UserOutlined />
          <strong>{record.full_name}</strong>
        </Space>
      ),
    },
    {
      title: 'Gender',
      dataIndex: 'gender',
      key: 'gender',
      width: 80,
      render: (gender: string) => (
        <Tag color={gender === 'M' ? 'blue' : 'pink'}>
          {gender === 'M' ? 'Male' : 'Female'}
        </Tag>
      ),
    },
    {
      title: 'Age',
      key: 'age',
      width: 80,
      render: (record: Athlete) => {
        if (!record.birth_date) return 'N/A';
        return calculateAge(record.birth_date);
      },
    },
    {
      title: 'Birth Date',
      dataIndex: 'birth_date',
      key: 'birth_date',
      render: (date: string) => date ? new Date(date).toLocaleDateString() : 'N/A',
    },
    {
      title: 'Country',
      dataIndex: 'country_name',
      key: 'country_name',
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: 'Disciplines',
      dataIndex: 'disciplines',
      key: 'disciplines',
      render: (disciplines: string[]) => (
        <div>
          {disciplines?.slice(0, 2).map((discipline, index) => (
            <Tag key={index} color="green" style={{ marginBottom: 2 }}>
              {discipline}
            </Tag>
          ))}
          {disciplines?.length > 2 && (
            <Tag color="default">+{disciplines.length - 2}</Tag>
          )}
        </div>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (record: Athlete) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => showAthleteDetails(record)}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>Athletes</Title>
      
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Search
            placeholder="Search athletes by name or country..."
            allowClear
            enterButton={<SearchOutlined />}
            size="large"
            onSearch={handleSearch}
            style={{ maxWidth: 400 }}
          />
        </Space>
      </Card>

      <Card>
        <Table
          columns={columns}
          dataSource={athletes}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} of ${total} athletes`,
          }}
          onChange={handleTableChange}
          scroll={{ x: 800 }}
        />
      </Card>

      <Modal
        title="Athlete Details"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedAthlete && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="Full Name" span={2}>
              {selectedAthlete.full_name}
            </Descriptions.Item>
            <Descriptions.Item label="Given Name">
              {selectedAthlete.given_name}
            </Descriptions.Item>
            <Descriptions.Item label="Family Name">
              {selectedAthlete.family_name}
            </Descriptions.Item>
            <Descriptions.Item label="Gender">
              <Tag color={selectedAthlete.gender === 'M' ? 'blue' : 'pink'}>
                {selectedAthlete.gender === 'M' ? 'Male' : 'Female'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Birth Date">
              {selectedAthlete.birth_date ? new Date(selectedAthlete.birth_date).toLocaleDateString() : 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Age">
              {selectedAthlete.birth_date ? calculateAge(selectedAthlete.birth_date) : 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Country">
              <Tag color="blue">{selectedAthlete.country_name}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Disciplines">
              {selectedAthlete.disciplines?.map((discipline, index) => (
                <Tag key={index} color="green" style={{ marginBottom: 4 }}>
                  {discipline}
                </Tag>
              ))}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default Athletes;
